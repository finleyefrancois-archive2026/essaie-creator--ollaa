/**
 * Currency Conversion Service for Mauritius ↔ Thailand Corridor
 * 
 * Handles FX conversion between MUR (Mauritius Rupee), THB (Thai Baht),
 * and USDC stablecoin with mock API for development.
 * 
 * Features:
 * - Real-time rate fetching (mock API)
 * - Rate locking for up to 24 hours (hedging)
 * - Multi-currency support
 */

// Supported currencies
export enum Currency {
  MUR = 'MUR', // Mauritius Rupee
  THB = 'THB', // Thai Baht
  USDC = 'USDC', // USD Coin (Stablecoin)
  USD = 'USD' // US Dollar
}

// Exchange rate interface
export interface ExchangeRate {
  from: Currency;
  to: Currency;
  rate: number;
  timestamp: number;
  validUntil: number; // Rate lock expiry
  source: 'market' | 'locked';
}

// Rate lock interface
export interface RateLock {
  id: string;
  fromAmount: number;
  fromCurrency: Currency;
  toCurrency: Currency;
  lockedRate: number;
  createdAt: number;
  expiresAt: number;
  status: 'active' | 'used' | 'expired';
}

// Mock exchange rates (in production, fetch from real API)
const MOCK_RATES: Record<string, number> = {
  'MUR_USD': 0.022,    // 1 MUR = 0.022 USD
  'USD_MUR': 45.45,    // 1 USD = 45.45 MUR
  'THB_USD': 0.029,    // 1 THB = 0.029 USD
  'USD_THB': 34.50,    // 1 USD = 34.50 THB
  'USDC_USD': 1.00,    // 1 USDC = 1.00 USD (stablecoin peg)
  'USD_USDC': 1.00     // 1 USD = 1.00 USDC
};

// Rate lock duration (24 hours)
const RATE_LOCK_DURATION_MS = 24 * 60 * 60 * 1000;

/**
 * Currency Conversion Service
 */
export class CurrencyConversionService {
  private rateLocks: Map<string, RateLock> = new Map();
  private readonly LOCK_PREFIX = 'ratelock_';

  constructor() {
    this.loadRateLocksFromStorage();
  }

  /**
   * Get current exchange rate between two currencies
   */
  async getExchangeRate(from: Currency, to: Currency): Promise<ExchangeRate> {
    // Direct conversion
    const directKey = `${from}_${to}`;
    if (MOCK_RATES[directKey]) {
      return {
        from,
        to,
        rate: MOCK_RATES[directKey],
        timestamp: Date.now(),
        validUntil: Date.now() + RATE_LOCK_DURATION_MS,
        source: 'market'
      };
    }

    // Convert via USD as intermediary
    const fromToUSD = `${from}_USD`;
    const usdToTo = `USD_${to}`;

    if (MOCK_RATES[fromToUSD] && MOCK_RATES[usdToTo]) {
      const crossRate = MOCK_RATES[fromToUSD] * MOCK_RATES[usdToTo];
      return {
        from,
        to,
        rate: crossRate,
        timestamp: Date.now(),
        validUntil: Date.now() + RATE_LOCK_DURATION_MS,
        source: 'market'
      };
    }

    throw new Error(`No exchange rate available for ${from} to ${to}`);
  }

  /**
   * Lock exchange rate for future transaction (hedging)
   * Returns a rate lock ID that can be used within 24 hours
   */
  async lockRate(
    fromAmount: number,
    fromCurrency: Currency,
    toCurrency: Currency
  ): Promise<RateLock> {
    const currentRate = await this.getExchangeRate(fromCurrency, toCurrency);
    
    const rateLock: RateLock = {
      id: this.generateLockId(),
      fromAmount,
      fromCurrency,
      toCurrency,
      lockedRate: currentRate.rate,
      createdAt: Date.now(),
      expiresAt: Date.now() + RATE_LOCK_DURATION_MS,
      status: 'active'
    };

    this.rateLocks.set(rateLock.id, rateLock);
    this.saveRateLocksToStorage();

    return rateLock;
  }

  /**
   * Execute conversion using a locked rate
   */
  executeLockedRate(lockId: string): { convertedAmount: number; rate: number } | null {
    const lock = this.rateLocks.get(lockId);

    if (!lock) {
      console.error(`Rate lock ${lockId} not found`);
      return null;
    }

    if (lock.status === 'expired') {
      console.error(`Rate lock ${lockId} has expired`);
      return null;
    }

    if (lock.status === 'used') {
      console.error(`Rate lock ${lockId} has already been used`);
      return null;
    }

    const convertedAmount = lock.fromAmount * lock.lockedRate;
    
    // Mark as used
    lock.status = 'used';
    this.rateLocks.set(lockId, lock);
    this.saveRateLocksToStorage();

    return {
      convertedAmount,
      rate: lock.lockedRate
    };
  }

  /**
   * Convert amount between currencies (instant conversion)
   */
  async convert(
    amount: number,
    fromCurrency: Currency,
    toCurrency: Currency
  ): Promise<{ convertedAmount: number; rate: number; fee: number }> {
    const rateInfo = await this.getExchangeRate(fromCurrency, toCurrency);
    const convertedAmount = amount * rateInfo.rate;
    
    // Calculate fee (0.5% spread for cross-border transfers)
    const fee = convertedAmount * 0.005;
    const finalAmount = convertedAmount - fee;

    return {
      convertedAmount: finalAmount,
      rate: rateInfo.rate,
      fee
    };
  }

  /**
   * Specialized function for Mauritius → Thailand corridor
   * Converts MUR → USDC → THB
   */
  async convertMURtoTHB(amountMUR: number): Promise<{
    murAmount: number;
    usdcAmount: number;
    thbAmount: number;
    totalFee: number;
    breakdown: {
      murToUsdc: { rate: number; fee: number };
      usdcToThb: { rate: number; fee: number };
    };
  }> {
    // Step 1: MUR → USDC
    const murToUsdc = await this.convert(amountMUR, Currency.MUR, Currency.USDC);
    
    // Step 2: USDC → THB
    const usdcToThb = await this.convert(murToUsdc.convertedAmount, Currency.USDC, Currency.THB);

    return {
      murAmount: amountMUR,
      usdcAmount: murToUsdc.convertedAmount,
      thbAmount: usdcToThb.convertedAmount,
      totalFee: murToUsdc.fee + usdcToThb.fee,
      breakdown: {
        murToUsdc: {
          rate: murToUsdc.rate,
          fee: murToUsdc.fee
        },
        usdcToThb: {
          rate: usdcToThb.rate,
          fee: usdcToThb.fee
        }
      }
    };
  }

  /**
   * Check if a rate lock is still valid
   */
  isRateLockValid(lockId: string): boolean {
    const lock = this.rateLocks.get(lockId);
    
    if (!lock) {
      return false;
    }

    if (lock.status !== 'active') {
      return false;
    }

    if (Date.now() > lock.expiresAt) {
      // Mark as expired
      lock.status = 'expired';
      this.rateLocks.set(lockId, lock);
      return false;
    }

    return true;
  }

  /**
   * Get remaining time on a rate lock (in minutes)
   */
  getRateLockRemainingTime(lockId: string): number | null {
    const lock = this.rateLocks.get(lockId);
    
    if (!lock) {
      return null;
    }

    const remaining = lock.expiresAt - Date.now();
    return Math.max(0, Math.floor(remaining / 60000)); // Convert to minutes
  }

  /**
   * Generate unique rate lock ID
   */
  private generateLockId(): string {
    const timestamp = Date.now().toString();
    const random = Math.random().toString(36).substring(2);
    return `${this.LOCK_PREFIX}${timestamp}_${random}`;
  }

  /**
   * Save rate locks to localStorage
   */
  private saveRateLocksToStorage(): void {
    const locksArray = Array.from(this.rateLocks.values());
    localStorage.setItem('olaa_rate_locks', JSON.stringify(locksArray));
  }

  /**
   * Load rate locks from localStorage
   */
  private loadRateLocksFromStorage(): void {
    const stored = localStorage.getItem('olaa_rate_locks');
    if (stored) {
      const locksArray: RateLock[] = JSON.parse(stored);
      locksArray.forEach(lock => {
        // Check if expired on load
        if (Date.now() > lock.expiresAt) {
          lock.status = 'expired';
        }
        this.rateLocks.set(lock.id, lock);
      });
    }
  }

  /**
   * Clean up expired rate locks
   */
  cleanupExpiredLocks(): void {
    const now = Date.now();
    let changed = false;

    for (const [id, lock] of this.rateLocks.entries()) {
      if (now > lock.expiresAt && lock.status === 'active') {
        lock.status = 'expired';
        this.rateLocks.set(id, lock);
        changed = true;
      }
    }

    if (changed) {
      this.saveRateLocksToStorage();
    }
  }

  /**
   * Get all active rate locks
   */
  getActiveRateLocks(): RateLock[] {
    return Array.from(this.rateLocks.values()).filter(
      lock => lock.status === 'active' && Date.now() <= lock.expiresAt
    );
  }
}

// Export singleton instance
export const currencyService = new CurrencyConversionService();

// Example usage for the Mauritius → Thailand use case:
/*
// Grandma wants to send 5,000 MUR to Thailand
const conversion = await currencyService.convertMURtoTHB(5000);

console.log(`Sending ${conversion.murAmount} MUR`);
console.log(`Converted to ${conversion.usdcAmount.toFixed(2)} USDC`);
console.log(`Grandchild receives ${conversion.thbAmount.toFixed(2)} THB`);
console.log(`Total fees: ${conversion.totalFee.toFixed(2)} THB`);
console.log('Breakdown:', conversion.breakdown);

// Lock rate for later use (up to 24 hours)
const rateLock = await currencyService.lockRate(5000, Currency.MUR, Currency.THB);
console.log(`Rate locked: ${rateLock.lockedRate}, expires in 24h`);

// Use locked rate later
const result = currencyService.executeLockedRate(rateLock.id);
if (result) {
  console.log(`Converted with locked rate: ${result.convertedAmount} THB`);
}
*/
