import os
import random
import datetime
from typing import Tuple, List, Dict
import numpy as np
import pandas as pd


# Predefined master data
CATEGORIES = [
    "Groceries",
    "Dining",
    "Electronics",
    "Luxury",
    "Travel",
    "Entertainment",
    "Crypto Exchange",
    "Wire Transfer",
    "Healthcare",
    "Retail",
]

PAYMENT_METHODS = ["CREDIT_CARD", "DEBIT_CARD", "WIRE_TRANSFER", "ACH", "CRYPTO"]

CITIES = [
    ("New York", "US"),
    ("San Francisco", "US"),
    ("Chicago", "US"),
    ("London", "UK"),
    ("Toronto", "CA"),
    ("Berlin", "DE"),
    ("Singapore", "SG"),
    ("Tokyo", "JP"),
    ("Sydney", "AU"),
    ("Lagos", "NG"),
]

MERCHANT_NAMES = {
    "Groceries": ["Whole Foods Market", "Trader Joe's", "Kroger", "Safeway", "ALDI"],
    "Dining": ["Sweetgreen", "Chipotle", "Nobu", "Starbucks", "Shake Shack"],
    "Electronics": ["Apple Store", "Best Buy", "Micro Center", "B&H Photo", "Newegg"],
    "Luxury": ["Rolex Boutique", "Louis Vuitton", "Gucci", "Tiffany & Co.", "Cartier"],
    "Travel": ["Delta Air Lines", "Marriott Hotels", "Airbnb", "Uber", "Expedia"],
    "Entertainment": ["Netflix", "Spotify", "AMC Theatres", "Steam Games", "Sony PlayStation"],
    "Crypto Exchange": ["Binance Pay", "Coinbase Pro", "Kraken Direct", "Crypto.com"],
    "Wire Transfer": ["Western Union", "MoneyGram", "Wise Transfer", "Global Remit"],
    "Healthcare": ["CVS Pharmacy", "Walgreens", "Quest Diagnostics", "CityMD"],
    "Retail": ["Amazon", "Target", "Walmart", "Costco", "Nordstrom"],
}


def generate_synthetic_dataset(
    num_transactions: int = 12000,
    num_customers: int = 500,
    num_merchants: int = 150,
    seed: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Generates synthetic financial data:
    - Customers DataFrame
    - Merchants DataFrame
    - Transactions DataFrame with realistic fraud anomalies
    """
    random.seed(seed)
    np.random.seed(seed)

    # 1. Generate Customers
    customers_data = []
    customer_ids = [f"C{1000 + i}" for i in range(num_customers)]
    for cid in customer_ids:
        city, country = random.choice(CITIES[:5])  # Mostly US/UK/CA
        avg_spend = round(float(np.random.gamma(shape=5, scale=20)), 2)  # ~$100 avg spend
        risk_profile = random.choices(["LOW", "MEDIUM", "HIGH"], weights=[0.85, 0.12, 0.03])[0]
        customers_data.append({
            "customer_id": cid,
            "name": f"Customer_{cid}",
            "email": f"{cid.lower()}@financialops-enterprise.com",
            "risk_profile": risk_profile,
            "avg_monthly_spend": round(avg_spend * 30, 2),
            "home_country": country,
            "home_city": city,
            "account_status": "ACTIVE",
            "created_at": datetime.datetime(2025, 1, 1) + datetime.timedelta(days=random.randint(0, 365)),
        })
    df_customers = pd.DataFrame(customers_data)
    customer_avg_map = {c["customer_id"]: c["avg_monthly_spend"] / 30.0 for c in customers_data}
    customer_city_map = {c["customer_id"]: (c["home_city"], c["home_country"]) for c in customers_data}

    # 2. Generate Merchants
    merchants_data = []
    merchant_ids = [f"M{2000 + i}" for i in range(num_merchants)]
    for mid in merchant_ids:
        cat = random.choice(CATEGORIES)
        name_choice = random.choice(MERCHANT_NAMES[cat]) + f" #{random.randint(10, 999)}"
        city, country = random.choice(CITIES)
        base_risk = 0.02
        if cat in ["Crypto Exchange", "Wire Transfer"]:
            base_risk = 0.25
        elif cat == "Luxury":
            base_risk = 0.15
        merchants_data.append({
            "merchant_id": mid,
            "name": name_choice,
            "category": cat,
            "base_risk_score": base_risk,
            "city": city,
            "country": country,
            "created_at": datetime.datetime(2025, 1, 1),
        })
    df_merchants = pd.DataFrame(merchants_data)
    merchant_cat_map = {m["merchant_id"]: m["category"] for m in merchants_data}

    # 3. Generate Transactions
    base_time = datetime.datetime(2026, 1, 1, 8, 0, 0)
    txns = []

    for i in range(num_transactions):
        txn_id = f"TXN-{100000 + i}"
        cid = random.choice(customer_ids)
        mid = random.choice(merchant_ids)
        m_cat = merchant_cat_map[mid]
        hist_avg = max(10.0, customer_avg_map[cid])
        home_city, home_country = customer_city_map[cid]

        # Time progression
        time_offset_minutes = int(i * (180.0 * 24.0 * 60.0 / num_transactions)) + random.randint(-15, 15)
        txn_time = base_time + datetime.timedelta(minutes=max(0, time_offset_minutes))

        # Determine if this transaction is an injected anomaly (~3.5%)
        is_fraud = random.random() < 0.035
        payment_method = random.choices(PAYMENT_METHODS, weights=[0.55, 0.30, 0.05, 0.07, 0.03])[0]
        status = "COMPLETED"
        loc = f"{home_city}, {home_country}"
        flagged_reason = None

        if not is_fraud:
            # Normal distribution around customer's average
            amount = round(float(np.random.normal(loc=hist_avg, scale=hist_avg * 0.25)), 2)
            amount = max(3.50, amount)
            risk_level = "LOW"
            anomaly_score = round(random.uniform(0.01, 0.28), 4)
            is_flagged = False
        else:
            # Inject one of realistic fraud typologies
            fraud_type = random.choice([
                "amount_spike",
                "velocity_drain",
                "impossible_location",
                "midnight_high_risk",
            ])

            if fraud_type == "amount_spike":
                amount = round(hist_avg * random.uniform(8.5, 25.0) + random.uniform(500, 3000), 2)
                flagged_reason = f"Extreme amount deviation: ${amount:.2f} is {amount / hist_avg:.1f}x higher than customer average (${hist_avg:.2f})"
                anomaly_score = round(random.uniform(0.78, 0.98), 4)
                risk_level = "HIGH"
                is_flagged = True
                status = "FLAGGED"

            elif fraud_type == "velocity_drain":
                amount = round(random.uniform(850.0, 4500.0), 2)
                flagged_reason = "Rapid transaction velocity burst detected within 15-minute window"
                anomaly_score = round(random.uniform(0.72, 0.91), 4)
                risk_level = "HIGH"
                is_flagged = True
                status = "FLAGGED"

            elif fraud_type == "impossible_location":
                foreign_city, foreign_country = random.choice(CITIES[5:])  # foreign remote
                loc = f"{foreign_city}, {foreign_country}"
                amount = round(hist_avg * random.uniform(2.5, 6.0), 2)
                flagged_reason = f"Geographic discrepancy: card used in {loc} while customer home location is {home_city}, {home_country}"
                anomaly_score = round(random.uniform(0.76, 0.95), 4)
                risk_level = "HIGH"
                is_flagged = True
                status = "FLAGGED"

            else:  # midnight_high_risk
                # Force high-risk category and payment method
                m_cat = random.choice(["Crypto Exchange", "Wire Transfer", "Luxury"])
                payment_method = random.choice(["CRYPTO", "WIRE_TRANSFER"])
                amount = round(random.uniform(1200.0, 9500.0), 2)
                # Force time to 03:00 AM
                txn_time = txn_time.replace(hour=3, minute=random.randint(5, 55))
                flagged_reason = f"High-risk {m_cat} transaction initiated via {payment_method} during non-standard hours (03:00 AM)"
                anomaly_score = round(random.uniform(0.82, 0.99), 4)
                risk_level = "HIGH"
                is_flagged = True
                status = "FLAGGED"

        txns.append({
            "transaction_id": txn_id,
            "customer_id": cid,
            "merchant_id": mid,
            "amount": amount,
            "currency": "USD",
            "timestamp": txn_time,
            "category": m_cat,
            "payment_method": payment_method,
            "status": status,
            "location": loc,
            "historical_avg_spending": round(hist_avg, 2),
            "anomaly_score": anomaly_score,
            "risk_level": risk_level,
            "is_flagged": is_flagged,
            "flagged_reason": flagged_reason,
            "is_fraud_ground_truth": 1 if is_fraud else 0,
            "created_at": txn_time,
        })

    df_txns = pd.DataFrame(txns)
    return df_customers, df_merchants, df_txns


def export_synthetic_datasets(target_dir: str = "data/raw") -> Dict[str, str]:
    """Generates and exports datasets to CSV."""
    os.makedirs(target_dir, exist_ok=True)
    df_customers, df_merchants, df_txns = generate_synthetic_dataset(num_transactions=12000)

    cust_path = os.path.join(target_dir, "customers.csv")
    merch_path = os.path.join(target_dir, "merchants.csv")
    txn_path = os.path.join(target_dir, "transactions.csv")

    df_customers.to_csv(cust_path, index=False)
    df_merchants.to_csv(merch_path, index=False)
    df_txns.to_csv(txn_path, index=False)

    return {
        "customers": cust_path,
        "merchants": merch_path,
        "transactions": txn_path,
        "total_transactions": len(df_txns),
        "total_customers": len(df_customers),
        "total_merchants": len(df_merchants),
    }


if __name__ == "__main__":
    result = export_synthetic_datasets()
    print("Synthetic dataset generated successfully:", result)
