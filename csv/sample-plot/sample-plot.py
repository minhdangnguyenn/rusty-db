import matplotlib.pyplot as plt

# Mock data for illustration (replace with your measured values later)
concurrency = [4, 32]  # low and high concurrency
tput_nocache = [8, 20]  # txns/s, no cache
tput_cache = [9, 30]  # txns/s, cache enabled

plt.figure(figsize=(5, 3))

plt.plot(concurrency, tput_nocache, marker="o", linestyle="-", label="Cache disabled")
plt.plot(concurrency, tput_cache, marker="s", linestyle="-", label="Cache enabled")

plt.xlabel("Client concurrency [threads]")
plt.ylabel("Throughput [txns/s]")
plt.title("Experiment 3: Interaction of Cache and Concurrency")
plt.xticks(concurrency)
plt.grid(True, linestyle="--", alpha=0.3)
plt.legend()

plt.tight_layout()
plt.savefig("exp3_interaction_throughput.png", dpi=300)
plt.show()
