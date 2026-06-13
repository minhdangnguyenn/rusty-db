use std::collections::HashMap;
use std::collections::HashSet;
use std::sync::LazyLock;
use std::sync::Mutex;
use std::sync::atomic::AtomicBool;
use std::sync::atomic::Ordering;
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
    index: HashMap<u64, usize>,
    cursor: usize,
}

impl Cache {
    fn new() -> Cache {
        Cache { entries: std::array::from_fn(|_| None), index: HashMap::new(), cursor: 0 }
    }
}

pub fn enable() {
    ENABLED.store(true, Relaxed);
}

pub fn is_enabled() -> bool {
    return ENABLED.load(Ordering::Relaxed);
}

//  filter_uncached(item) -> [ids_missing_from_cache]
pub fn filter_uncached(ids: &HashSet<u64>) -> Vec<u64> {
    if !is_enabled() {
        return ids.iter().copied().collect();
    }
    let cache = CACHE.lock().unwrap();
    ids.iter().filter(|id| !cache.index.contains_key(id)).copied().collect()
}

pub fn insert(id: u64, value: String) {
    if !is_enabled() {
        return;
    }
    let mut cache = CACHE.lock().unwrap();
    if let Some(&pos) = cache.index.get(&id) {
        // already cached, then update value in-place
        if let Some(entry) = &mut cache.entries[pos] {
            entry.value = value;
        }
    } else {
        // evict slot if occupied
        let pos = cache.cursor;
        if let Some(old) = cache.entries[pos].take() {
            cache.index.remove(&old.key);
        }
        cache.entries[pos] = Some(Entry { key: id, value });
        cache.index.insert(id, pos);
        cache.cursor = (pos + 1) % CACHE_SIZE;
    }
}
