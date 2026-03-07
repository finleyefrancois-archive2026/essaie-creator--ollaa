/**
 * Offline-First Transaction Queue Service
 * 
 * Handles store-and-forward mechanism for transactions created offline.
 * Encrypts data locally using AES-256 before syncing when connectivity is restored.
 * Implements idempotency to prevent double-spending on sync failures.
 */

// Transaction status enum
export enum TransactionStatus {
  PENDING = 'pending',
  ENCRYPTED = 'encrypted',
  SYNCING = 'syncing',
  COMPLETED = 'completed',
  FAILED = 'failed'
}

// Transaction interface
export interface Transaction {
  id: string;
  amount: number;
  currency: string;
  recipientPhone: string;
  timestamp: number;
  status: TransactionStatus;
  encryptedData?: string;
  retryCount: number;
  maxRetries: number;
}

// Encrypted transaction payload
interface EncryptedPayload {
  iv: string; // Initialization vector
  data: string; // Encrypted transaction data
  authTag: string; // Authentication tag for AES-GCM
}

/**
 * Offline Transaction Queue Manager
 */
export class OfflineTransactionQueue {
  private queue: Transaction[] = [];
  private readonly STORAGE_KEY = 'olaa_offline_transactions';
  private readonly ENCRYPTION_KEY_NAME = 'olaa_encryption_key';
  private syncInProgress = false;
  private readonly MAX_RETRIES = 3;

  constructor() {
    this.loadFromStorage();
    this.setupNetworkListener();
  }

  /**
   * Add a new transaction to the offline queue
   */
  async addTransaction(transaction: Omit<Transaction, 'id' | 'status' | 'retryCount' | 'maxRetries'>): Promise<string> {
    const newTransaction: Transaction = {
      ...transaction,
      id: this.generateIdempotencyId(),
      status: TransactionStatus.PENDING,
      retryCount: 0,
      maxRetries: this.MAX_RETRIES
    };

    // Encrypt the transaction data
    const encryptedPayload = await this.encryptTransaction(newTransaction);
    newTransaction.encryptedData = JSON.stringify(encryptedPayload);
    newTransaction.status = TransactionStatus.ENCRYPTED;

    this.queue.push(newTransaction);
    await this.saveToStorage();

    // Attempt immediate sync if online
    if (navigator.onLine) {
      this.syncQueue();
    }

    return newTransaction.id;
  }

  /**
   * Generate unique idempotency ID to prevent double-spending
   */
  private generateIdempotencyId(): string {
    const timestamp = Date.now().toString();
    const random = Math.random().toString(36).substring(2);
    return `txn_${timestamp}_${random}`;
  }

  /**
   * Encrypt transaction data using Web Crypto API (AES-256-GCM)
   */
  private async encryptTransaction(transaction: Transaction): Promise<EncryptedPayload> {
    // Get or create encryption key
    const key = await this.getEncryptionKey();

    // Prepare data to encrypt (exclude sensitive fields that don't need encryption)
    const dataToEncrypt = JSON.stringify({
      amount: transaction.amount,
      currency: transaction.currency,
      recipientPhone: transaction.recipientPhone
    });

    // Convert to Uint8Array
    const encoder = new TextEncoder();
    const data = encoder.encode(dataToEncrypt);

    // Generate random IV (12 bytes for AES-GCM)
    const iv = crypto.getRandomValues(new Uint8Array(12));

    // Encrypt using AES-GCM
    const encrypted = await crypto.subtle.encrypt(
      {
        name: 'AES-GCM',
        iv: iv
      },
      key,
      data
    );

    // Extract authentication tag (last 16 bytes)
    const encryptedBytes = new Uint8Array(encrypted);
    const authTag = encryptedBytes.slice(-16);
    const actualData = encryptedBytes.slice(0, -16);

    return {
      iv: this.arrayBufferToBase64(iv),
      data: this.arrayBufferToBase64(actualData.buffer),
      authTag: this.arrayBufferToBase64(authTag.buffer)
    };
  }

  /**
   * Decrypt transaction data
   */
  private async decryptTransaction(encryptedPayload: EncryptedPayload): Promise<any> {
    const key = await this.getEncryptionKey();

    const iv = this.base64ToArrayBuffer(encryptedPayload.iv);
    const data = this.base64ToArrayBuffer(encryptedPayload.data);
    const authTag = this.base64ToArrayBuffer(encryptedPayload.authTag);

    // Combine data and auth tag
    const encryptedBytes = new Uint8Array(data.byteLength + authTag.byteLength);
    encryptedBytes.set(new Uint8Array(data), 0);
    encryptedBytes.set(new Uint8Array(authTag), data.byteLength);

    const decrypted = await crypto.subtle.decrypt(
      {
        name: 'AES-GCM',
        iv: new Uint8Array(iv)
      },
      key,
      encryptedBytes
    );

    const decoder = new TextDecoder();
    return JSON.parse(decoder.decode(decrypted));
  }

  /**
   * Get or create AES-256 encryption key
   */
  private async getEncryptionKey(): Promise<CryptoKey> {
    const storedKey = localStorage.getItem(this.ENCRYPTION_KEY_NAME);

    if (storedKey) {
      const keyData = JSON.parse(storedKey);
      return await crypto.subtle.importKey(
        'jwk',
        keyData,
        { name: 'AES-GCM', length: 256 },
        true,
        ['encrypt', 'decrypt']
      );
    }

    // Generate new key
    const key = await crypto.subtle.generateKey(
      { name: 'AES-GCM', length: 256 },
      true,
      ['encrypt', 'decrypt']
    );

    // Export and store key
    const exportedKey = await crypto.subtle.exportKey('jwk', key);
    localStorage.setItem(this.ENCRYPTION_KEY_NAME, JSON.stringify(exportedKey));

    return key;
  }

  /**
   * Sync queued transactions to backend
   */
  async syncQueue(): Promise<void> {
    if (this.syncInProgress || !navigator.onLine) {
      return;
    }

    this.syncInProgress = true;

    try {
      const pendingTransactions = this.queue.filter(
        t => t.status === TransactionStatus.ENCRYPTED && t.retryCount < t.maxRetries
      );

      for (const transaction of pendingTransactions) {
        await this.syncSingleTransaction(transaction);
      }
    } finally {
      this.syncInProgress = false;
      await this.saveToStorage();
    }
  }

  /**
   * Sync individual transaction with idempotency check
   */
  private async syncSingleTransaction(transaction: Transaction): Promise<void> {
    transaction.status = TransactionStatus.SYNCING;
    transaction.retryCount++;

    try {
      // Decrypt transaction for sending
      const decryptedData = await this.decryptTransaction(
        JSON.parse(transaction.encryptedData!)
      );

      // Send to backend with idempotency key
      const response = await fetch('/api/transactions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Idempotency-Key': transaction.id,
          'X-Olaa-Client-Version': '1.0.0'
        },
        body: JSON.stringify({
          id: transaction.id,
          ...decryptedData,
          timestamp: transaction.timestamp
        })
      });

      if (response.ok) {
        transaction.status = TransactionStatus.COMPLETED;
        // Remove from queue after successful sync
        this.queue = this.queue.filter(t => t.id !== transaction.id);
      } else {
        throw new Error(`Sync failed with status: ${response.status}`);
      }
    } catch (error) {
      console.error(`Failed to sync transaction ${transaction.id}:`, error);
      
      if (transaction.retryCount >= transaction.maxRetries) {
        transaction.status = TransactionStatus.FAILED;
        // Keep failed transactions for manual review
      } else {
        transaction.status = TransactionStatus.ENCRYPTED;
      }
    }
  }

  /**
   * Setup network status listener for automatic sync
   */
  private setupNetworkListener(): void {
    window.addEventListener('online', () => {
      console.log('Network restored, syncing queued transactions...');
      this.syncQueue();
    });

    window.addEventListener('offline', () => {
      console.log('Network lost, queuing transactions offline');
    });
  }

  /**
   * Save queue to local storage
   */
  private async saveToStorage(): Promise<void> {
    localStorage.setItem(this.STORAGE_KEY, JSON.stringify(this.queue));
  }

  /**
   * Load queue from local storage
   */
  private loadFromStorage(): void {
    const stored = localStorage.getItem(this.STORAGE_KEY);
    if (stored) {
      this.queue = JSON.parse(stored);
    }
  }

  /**
   * Get queue status
   */
  getQueueStatus(): { pending: number; completed: number; failed: number } {
    return {
      pending: this.queue.filter(t => t.status === TransactionStatus.ENCRYPTED).length,
      completed: this.queue.filter(t => t.status === TransactionStatus.COMPLETED).length,
      failed: this.queue.filter(t => t.status === TransactionStatus.FAILED).length
    };
  }

  /**
   * Utility: ArrayBuffer to Base64
   */
  private arrayBufferToBase64(buffer: ArrayBuffer): string {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  }

  /**
   * Utility: Base64 to ArrayBuffer
   */
  private base64ToArrayBuffer(base64: string): ArrayBuffer {
    const binaryString = atob(base64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes.buffer;
  }
}

// Export singleton instance
export const offlineQueue = new OfflineTransactionQueue();
