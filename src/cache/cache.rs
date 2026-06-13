use std::collections::HashMap;
use std::collections::HashSet;
use std::sync::LazyLock;
use std::sync::Mutex;
use std::sync::atomic::AtomicBool;
use std::sync::atomic::Ordering;
use std::sync::atomic::Ordering::Relaxed;

static ENABLED: AtomicBool = AtomicBool::new(false);
static CACHE: LazyLock<Mutex<HashMap<u64, String>>> = LazyLock::new(|| Mutex::new(HashMap::new()));

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
    ids.iter().filter(|id| !cache.contains_key(id)).copied().collect()
}

pub fn insert(id: u64, value: String) {
    if !is_enabled() {
        return;
    }
    let mut cache = CACHE.lock().unwrap();
    cache.insert(id, value);
}
