use rand::distr::Distribution;
use rand::rngs::StdRng;
use toydb::error::Result;

/// Key distribution for workloads.
#[derive(Clone, Copy)]
pub enum KeyDist {
    Uniform(rand::distr::Uniform<u64>),
    Zipf(rand_distr::Zipf<f64>),
}

impl KeyDist {
    pub fn sample(&self, rng: &mut StdRng) -> u64 {
        match self {
            KeyDist::Uniform(d) => d.sample(rng),
            KeyDist::Zipf(d) => d.sample(rng) as u64,
        }
    }
}

/// Distribution kind for CLI argument.
#[derive(clap::ValueEnum, Clone, Debug)]
pub enum DistKind {
    Uniform,
    Zipf,
}

/// Shared distribution arguments for workloads.
#[derive(clap::Args, Clone, Debug)]
pub struct DistArgs {
    /// Key distribution to use (uniform or zipf).
    #[arg(long, default_value = "uniform")]
    pub dist: DistKind,

    /// Zipf exponent (higher = more skewed, only used with --dist zipf).
    #[arg(long, default_value_t = 1.0)]
    pub skew: f64,
}

impl DistArgs {
    pub fn build(&self, num_elements: u64) -> Result<KeyDist> {
        match self.dist {
            DistKind::Uniform => Ok(KeyDist::Uniform(
                rand::distr::Uniform::new(1, num_elements + 1)?,
            )),
            DistKind::Zipf => Ok(KeyDist::Zipf(rand_distr::Zipf::new(
                num_elements as f64,
                self.skew,
            )?)),
        }
    }
}

impl std::fmt::Display for DistArgs {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self.dist {
            DistKind::Uniform => write!(f, "dist=uniform"),
            DistKind::Zipf => write!(f, "dist=zipf skew={}", self.skew),
        }
    }
}
