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

struct Cache {
    entries: HashMap<u64, String>,
    access_history: Vec<u64>,
    cursor: usize,
}

impl Cache {
    fn new() -> Cache {
        Cache { access_history: Vec::new(), entries: HashMap::new(), cursor: 0 }
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
    let mut uncached = Vec::new();
    for key in keys.iter() {
        if cache.entries.contains_key(key) {
            HITS.fetch_add(1, Relaxed);
            if EVICT_TYPE.load(Relaxed) == EvictType::LRU as u8 {
                cache.access_history.retain(|k| k != key);
                cache.access_history.push(*key);
            }
        } else {
            MISSES.fetch_add(1, Relaxed);
            uncached.push(*key);
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

fn evict(cache: &mut Cache, evict_type: EvictType) {
    loop {
        if cache.cursor >= cache.access_history.len() {
            cache.cursor = 0;
        }
        if evict_type == EvictType::LRU {
            let candidate = cache.access_history[cache.cursor];
            cache.cursor += 1;
            if cache.entries.contains_key(&candidate) {
                cache.entries.remove(&candidate);
                break;
            }
        } else if evict_type == EvictType::FIFO {
            if let Some(&candidate) = cache.access_history.first() {
                cache.entries.remove(&candidate);
            }
            break;
        }
    }
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
    cache.entries.insert(key, value);
    cache.access_history.push(key);
    // when need evict
    if cache.entries.len() > MAX_SIZE.load(Relaxed) {
        let ty = match EVICT_TYPE.load(Relaxed) {
            1 => EvictType::FIFO,
            _ => EvictType::LRU,
        };
        evict(&mut cache, ty);
    }
}
