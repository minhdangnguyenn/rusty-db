use std::collections::HashMap;
use std::collections::HashSet;
use std::sync::LazyLock;
use std::sync::Mutex;
use std::sync::atomic::AtomicBool;
use std::sync::atomic::AtomicU8;
use std::sync::atomic::AtomicU64;
use std::sync::atomic::AtomicUsize;
use std::sync::atomic::Ordering::Relaxed;

static ENABLED: AtomicBool = AtomicBool::new(false);
static CACHE: LazyLock<Mutex<Cache>> = LazyLock::new(|| Mutex::new(Cache::new()));
static HITS: AtomicU64 = AtomicU64::new(0);
static MISSES: AtomicU64 = AtomicU64::new(0);
static EVICT_TYPE: AtomicU8 = AtomicU8::new(0); // LRU
static MAX_SIZE: AtomicUsize = AtomicUsize::new(5000);

#[derive(PartialEq, Eq, Clone, Copy)]
#[allow(clippy::upper_case_acronyms)]
#[repr(u8)]
pub enum EvictType {
    LRU = 0,
    FIFO = 1,
}

struct CacheEntry {
    value: String,
    prev: Option<u64>,
    next: Option<u64>,
}

struct Cache {
    entries: HashMap<u64, CacheEntry>,
    head: Option<u64>, // MRU end
    tail: Option<u64>, // LRU end
}

impl Cache {
    fn new() -> Cache {
        Cache { entries: HashMap::new(), head: None, tail: None }
    }

    fn detach(&mut self, key: u64) {
        let (prev, next) = {
            let entry = self.entries.get(&key).expect("key must exist");
            (entry.prev, entry.next)
        };
        match prev {
            Some(p) => self.entries.get_mut(&p).unwrap().next = next,
            None => self.head = next,
        }
        match next {
            Some(n) => self.entries.get_mut(&n).unwrap().prev = prev,
            None => self.tail = prev,
        }
    }

    fn attach_to_front(&mut self, key: u64) {
        let old_head = self.head;
        {
            let entry = self.entries.get_mut(&key).unwrap();
            entry.prev = None;
            entry.next = old_head;
        }
        match old_head {
            Some(old) => self.entries.get_mut(&old).unwrap().prev = Some(key),
            None => self.tail = Some(key),
        }
        self.head = Some(key);
    }

    fn pop_tail(&mut self) -> Option<u64> {
        let key = self.tail?;
        self.detach(key);
        Some(key)
    }
}

pub fn enable() {
    ENABLED.store(true, Relaxed);
}

pub fn is_enabled() -> bool {
    ENABLED.load(Relaxed)
}

pub fn set_eviction(ty: EvictType) {
    EVICT_TYPE.store(ty as u8, Relaxed);
}

pub fn set_max_size(size: usize) {
    MAX_SIZE.store(size, Relaxed);
}

pub fn filter_uncached(keys: &HashSet<u64>) -> Vec<u64> {
    if !is_enabled() {
        return keys.iter().copied().collect();
    }
    let mut cache = CACHE.lock().unwrap();
    let evict_type = EVICT_TYPE.load(Relaxed);
    let mut uncached = Vec::new();

    for &key in keys {
        if cache.entries.contains_key(&key) {
            HITS.fetch_add(1, Relaxed);
            if evict_type == EvictType::LRU as u8 {
                cache.detach(key);
                cache.attach_to_front(key);
            }
        } else {
            MISSES.fetch_add(1, Relaxed);
            uncached.push(key);
        }
    }
    uncached
}

pub fn stats() -> (u64, u64, f64) {
    let hits = HITS.load(Relaxed);
    let misses = MISSES.load(Relaxed);
    let ratio = if hits + misses > 0 { hits as f64 / (hits + misses) as f64 } else { 0.0 };
    (hits, misses, ratio)
}

pub fn reset_stats() {
    HITS.store(0, Relaxed);
    MISSES.store(0, Relaxed);
}

pub fn insert(key: u64, value: String) {
    if !is_enabled() {
        return;
    }
    let mut cache = CACHE.lock().unwrap();
    let max_size = MAX_SIZE.load(Relaxed);

    if let Some(entry) = cache.entries.get_mut(&key) {
        entry.value = value;
        if EVICT_TYPE.load(Relaxed) == EvictType::LRU as u8 {
            cache.detach(key);
            cache.attach_to_front(key);
        }
        return;
    }

    cache.entries.insert(key, CacheEntry { value, prev: None, next: None });
    cache.attach_to_front(key);

    if cache.entries.len() > max_size {
        if let Some(victim) = cache.pop_tail() {
            cache.entries.remove(&victim);
        }
    }
}
