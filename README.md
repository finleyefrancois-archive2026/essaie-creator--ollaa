# OpenLedger Access (OLA) - "Olaa"

**Tagline:** Fuel for Life  
**Mission:** Democratize corporate-grade financial logistics for the unbanked via a mobile-first, offline-capable web application.

---

## ⚠️ Brand Notice: "Olaa" vs "Ola Finance"

This project uses the name **"Olaa"** (pronounced Oh-lah-ah, 3 syllables) with deliberate differentiation from "Ola Finance":

| Factor | Ola Finance | Olaa (This Project) |
|--------|-------------|---------------------|
| **Spelling** | O-L-A | O-L-A-A (double 'a') |
| **Service** | DeFi Lending | P2P Remittance |
| **Target Users** | Crypto natives | Unbanked families |
| **Geography** | Global/DeFi | Mauritius → Thailand corridor |
| **Tagline** | DeFi Lending | "Fuel for Life" |

**Trademark Status:** Pending legal clearance (Phase 0, Week 1-2)

---

## 📁 Project Structure

```
/workspace
├── src/
│   ├── frontend/          # PWA (Progressive Web App)
│   │   ├── components/    # UI components
│   │   ├── services/      # API clients, encryption
│   │   ├── workers/       # Service Workers (offline-first)
│   │   └── styles/        # CSS, themes (Grandmother Mode)
│   ├── backend/           # Edge functions, APIs
│   │   ├── workers/       # Cloudflare Workers / Lambda@Edge
│   │   ├── api/           # GraphQL schema & resolvers
│   │   └── services/      # KYC, FX, blockchain rails
│   └── shared/            # Shared types, utilities
├── docs/                  # Documentation
├── legal/                 # Trademark, compliance docs
├── tests/                 # Test suites
└── scripts/               # Build & deployment scripts
```

---

## 🚀 Development Phases

### Phase 0: Validation (Current)
- [x] Repository initialization
- [ ] Trademark search ("Olaa" in MU, TH, US/EU)
- [ ] Domain acquisition (olaa.app, olaa.money, getolaa.com)
- [ ] Legal opinion on brand differentiation
- [ ] Social media handle reservation

### Phase 1: The Vault (MVP)
- [ ] PWA shell with offline-first architecture
- [ ] Digital wallet (stablecoin only)
- [ ] e-KYC implementation
- [ ] Internal transfers between test users

### Phase 2: The Bridge (Fiat Integration)
- [ ] Mauritius Mobile Money API integration (MCB Juice)
- [ ] Thailand PromptPay API integration
- [ ] Agent QR Code system
- [ ] Agent Finder map

### Phase 3: The Intelligence (Automation)
- [ ] Auto-FX hedging
- [ ] Voice navigation (Text-to-Speech)
- [ ] Offline transaction queuing with AES-256 encryption

---

## 🛡️ Security & Compliance

- **e-KYC:** ID scan + liveness check (no paperwork)
- **Encryption:** AES-256 for local data storage
- **Authentication:** WebAuthn (biometric, passwordless)
- **Compliance:** FATF Travel Rule, AML/KYC standards
- **Multi-Sig:** For large transactions
- **Emergency Freeze:** Panic button for lost devices

---

## 💰 Financial Rails

1. **Stablecoin Rail:** USDC/USDT on Solana/Stellar/Polygon
2. **Local Fiat:** MCB Juice (Mauritius), PromptPay (Thailand)
3. **P2P Liquidity:** Net out transfers without crossing borders

---

## 🌍 Primary Corridor: Mauritius → Thailand

**Use Case:** Grandmother in Mauritius sends birthday money to grandchildren in Thailand.

**Flow:**
1. Grandma scans ID + selfie → verified in <3 min
2. Links MCB Juice or deposits at OLA agent
3. Sends 5,000 MUR → converted to USDC
4. USDC transferred over Stellar/Solana ($0.01, 3 seconds)
5. Grandchild in Thailand receives SMS/WhatsApp notification
6. Grandchild completes lightweight e-KYC
7. Cash out to PromptPay or 7-Eleven via QR code
8. Grandma receives photo confirmation

---

## 📋 Critical Success Factors

- [ ] **Latency:** App loads in <2 seconds on 3G
- [ ] **Accessibility:** Usable by elderly with poor eyesight
- [ ] **Liquidity:** Sufficient agents in Thailand for cash-out
- [ ] **Compliance:** Meets FATF Travel Rule standards
- [ ] **Trust:** Visible guarantee fund/insurance for deposits

---

## 📞 Partnerships Required

1. **Local Payment Processors:** MCB (Mauritius), Thai bank/wallet provider
2. **Stablecoin Issuer:** Circle (USDC) or Tether
3. **Regulatory License:** Money Transmitter or EMI license (Singapore/UK)
4. **KYC Provider:** SumSub, Jumio, or similar
5. **Agent Network:** Convenience stores, post offices, mobile money agents

---

## 📄 License

[To be determined based on jurisdiction and licensing strategy]

---

## 🙏 Acknowledgments

This project blueprint is designed to empower individuals with the same financial power as corporations, focusing on the unbanked population in emerging markets.

**Core Philosophy:** *"Corporate Tools for Individuals." If a bank can move money instantly, a grandmother should be able to as well.*
