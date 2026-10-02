import { RateLimit } from './rate-limits';

/** Limiteur simple : file d'attente FIFO + concurrence max + espacement minimal. */
export class RateLimiter {
  private active = 0;
  private lastStart = 0;
  private timer: NodeJS.Timeout | null = null;
  private readonly queue: Array<() => void> = [];

  constructor(private readonly limit: RateLimit) {}

  async schedule<T>(task: () => Promise<T>): Promise<T> {
    await this.acquire();
    try {
      return await task();
    } finally {
      this.active--;
      this.next();
    }
  }

  private acquire(): Promise<void> {
    return new Promise((resolve) => {
      this.queue.push(resolve);
      this.next();
    });
  }

  private next(): void {
    if (this.timer || this.active >= this.limit.concurrency || this.queue.length === 0) return;
    const wait = this.lastStart + this.limit.minIntervalMs - Date.now();
    if (wait > 0) {
      this.timer = setTimeout(() => {
        this.timer = null;
        this.next();
      }, wait);
      return;
    }
    const resolve = this.queue.shift()!;
    this.active++;
    this.lastStart = Date.now();
    resolve();
    this.next();
  }
}
