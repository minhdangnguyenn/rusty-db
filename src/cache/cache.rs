use std::collections::HashSet;
use std::sync::LazyLock;
use std::sync::Mutex;
use std::sync::atomic::AtomicBool;
use std::sync::atomic::Ordering::Relaxed;

static ENABLED: AtomicBool = AtomicBool::new(false);
static CACHE: LazyLock<Mutex<Cache>> = LazyLock::new(|| Mutex::new(Cache::new()));

const CACHE_SIZE: usize = 5000;
struct Entry {
    key: u64,
    value: String,
}

struct Cache {
    entries: [Option<Entry>; CACHE_SIZE],
}

impl Cache {
    fn new() -> Cache {
        Cache { entries: std::array::from_fn(|_| None) }
    }
}

pub fn enable() {
    ENABLED.store(true, Relaxed);
}

pub fn is_enabled() -> bool {
    ENABLED.load(Relaxed)
}

pub fn filter_uncached(ids: &HashSet<u64>) -> Vec<u64> {
    if !is_enabled() {
        return ids.iter().copied().collect();
    }
    let mut cache = CACHE.lock().unwrap();
    let mut uncached = Vec::new();
    for &id in ids {
        let mut found = None;
        for pos in 0..CACHE_SIZE {
            if let Some(ref entry) = cache.entries[pos]
                && entry.key == id
            {
                found = Some(pos);
                break;
            }
        }
        if let Some(pos) = found {
            move_to_front(&mut cache, pos);
        } else {
            uncached.push(id);
        }
    }
    uncached
}

pub fn insert(id: u64, value: String) {
    if !is_enabled() {
        return;
    }
    let mut cache = CACHE.lock().unwrap();
    for pos in 0..CACHE_SIZE {
        if let Some(ref entry) = cache.entries[pos]
            && entry.key == id
        {
            cache.entries[pos].as_mut().unwrap().value = value;
            move_to_front(&mut cache, pos);
            return;
        }
    }
    for i in (0..CACHE_SIZE - 1).rev() {
        cache.entries[i + 1] = cache.entries[i].take();
    }
    cache.entries[0] = Some(Entry { key: id, value });
}

fn move_to_front(cache: &mut Cache, pos: usize) {
    let entry = cache.entries[pos].take();
    for i in (0..pos).rev() {
        cache.entries[i + 1] = cache.entries[i].take();
    }
    cache.entries[0] = entry;
}
