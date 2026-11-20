#!/usr/bin/env python3
"""ShopFlow fake log generator.

Writes CSV, JSON (one object per line) and TXT files that match the three
Logstash pipelines. Story built into the data:
  1. normal shop traffic: visit > search > product > cart > checkout > payment
  2. payment incident on the last day, 14:00-14:15 (gateway timeouts)
  3. fraud 1: card testing (many declined payments from one IP, one session)
  4. fraud 2: velocity (same user paying from 3 countries within minutes)
"""
import argparse
import csv
import itertools
import json
import os
from collections import OrderedDict
from datetime import date, datetime, timedelta

from faker import Faker

COLUMNS = ["timestamp", "level", "service", "event", "message", "order_id", "user_id",
           "session_id", "product_id", "amount", "payment_method", "response_ms", "client_ip"]

# traffic per hour of the day (index = hour): quiet at night, peaks at noon and evening
HOUR_WEIGHTS = [1, 1, 1, 1, 1, 2, 3, 5, 8, 10, 12, 12, 12, 12, 14, 14, 13, 12, 14, 16, 16, 12, 6, 3]

# first three numbers of public IPs: Tunisia (x3), France, Germany, USA
IP_PREFIXES = ["41.226.10", "41.226.11", "196.203.1", "90.84.12", "79.222.8", "98.137.4"]
PAYMENT_METHODS = OrderedDict([("card", 0.70), ("paypal", 0.15), ("cash_on_delivery", 0.15)])

Faker.seed(42)
fake = Faker()
rnd = fake.random          # seeded random generator: same seed, same data

PRODUCTS = {"P-%02d" % i: fake.random_int(990, 29900) / 100 for i in range(1, 41)}
order_counter = itertools.count(10000)


def ts_str(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def random_ip(prefix=None):
    return "%s.%d" % (prefix or rnd.choice(IP_PREFIXES), rnd.randint(2, 250))


class Day:
    """Collects the records of one day, then writes the 3 files."""

    def __init__(self, day):
        self.day = day
        self.csv, self.json, self.txt = [], [], []

    def log_csv(self, t, level, service, event, message, **kw):
        row = {c: "" for c in COLUMNS}
        row.update(timestamp=ts_str(t), level=level, service=service, event=event, message=message)
        row.update({k: v for k, v in kw.items() if v is not None})
        self.csv.append((t, row))

    def log_json(self, t, level, service, event, message, **kw):
        row = dict(timestamp=ts_str(t), level=level, service=service, event=event, message=message)
        row.update({k: v for k, v in kw.items() if v not in (None, "")})
        self.json.append((t, row))

    def log_txt(self, t, level, service, message):
        self.txt.append((t, "%s [%s] %s: %s" % (ts_str(t), level, service, message)))

    def payment(self, t, user, sess, ip, product, amount, method, outcome):
        """One payment attempt = 1 CSV line (payment-api) + 1 TXT line (gateway)
        + 1 JSON line (checkout result)."""
        order = "ORD-%d" % next(order_counter)
        if outcome == "success":
            lvl, ev, msg, ms = "INFO", "PAYMENT_SUCCESS", "Payment accepted", rnd.randint(150, 600)
        elif outcome == "declined":
            lvl, ev, msg, ms = "WARN", "CARD_DECLINED", "Card declined by provider", rnd.randint(200, 800)
        else:
            lvl, ev, msg, ms = "ERROR", "PAYMENT_TIMEOUT", "Gateway timeout", rnd.randint(4800, 5200)
        self.log_csv(t, lvl, "payment-api", ev, msg, order_id=order, user_id=user, session_id=sess,
                     product_id=product, amount="%.2f" % amount, payment_method=method,
                     response_ms=ms, client_ip=ip)
        self.log_txt(t + timedelta(seconds=1), lvl, "payment-gateway", "%s order=%s" % (msg, order))
        if outcome == "success":
            self.log_json(t + timedelta(seconds=2), "INFO", "checkout", "ORDER_CREATED", "Order created",
                          order_id=order, user_id=user, session_id=sess, amount=amount,
                          response_ms=rnd.randint(100, 400), client_ip=ip)
        else:
            self.log_json(t + timedelta(seconds=2), "ERROR", "checkout", "ORDER_FAILED",
                          "Order creation failed", order_id=order, user_id=user, session_id=sess,
                          response_ms=rnd.randint(500, 1500), client_ip=ip)

    def session(self, n):
        """One customer going through the funnel; many leave before paying."""
        sid = "S-%s%04d" % (self.day.strftime("%m%d"), n)
        user, ip = "U-%d" % rnd.randint(100, 999), random_ip()
        hour = rnd.choices(range(24), HOUR_WEIGHTS)[0]
        t = datetime.combine(self.day, datetime.min.time()) + timedelta(
            hours=hour, minutes=rnd.randint(0, 59), seconds=rnd.randint(0, 59))

        def step(service, event, msg, **kw):
            nonlocal t
            t += timedelta(seconds=rnd.randint(2, 40))
            self.log_csv(t, "INFO", service, event, msg, user_id=user, session_id=sid,
                         response_ms=rnd.randint(30, 400), client_ip=ip, **kw)

        step("web", "PAGE_VIEW", "Home page")
        if rnd.random() > 0.70:
            return
        step("search", "SEARCH", "Search query")
        if rnd.random() > 0.80:
            return
        product = rnd.choice(list(PRODUCTS))
        step("catalog", "PRODUCT_VIEW", "Product page", product_id=product)
        if rnd.random() > 0.40:
            return
        step("cart", "ADD_TO_CART", "Item added", product_id=product)
        if rnd.random() > 0.60:
            return
        t += timedelta(seconds=rnd.randint(5, 60))
        self.log_json(t, "INFO", "checkout", "CHECKOUT_START", "Checkout started",
                      user_id=user, session_id=sid, client_ip=ip)
        if rnd.random() > 0.85:
            return
        outcome = rnd.choices(["success", "declined", "timeout"], [90, 6, 4])[0]
        self.payment(t + timedelta(seconds=rnd.randint(20, 90)), user, sid, ip, product,
                     PRODUCTS[product], fake.random_element(PAYMENT_METHODS), outcome)

    def incident(self, count=70):
        """Payment gateway problem 14:00-14:15: a burst of timeouts."""
        start = datetime.combine(self.day, datetime.min.time()) + timedelta(hours=14)
        for i in range(count):
            t = start + timedelta(seconds=rnd.randint(0, 14 * 60 + 59))
            self.payment(t, "U-%d" % rnd.randint(100, 999), "S-INC%04d" % i, random_ip(),
                         rnd.choice(list(PRODUCTS)), rnd.randint(2000, 25000) / 100,
                         "card", "timeout" if rnd.random() < 0.9 else "declined")

    def fraud_card_testing(self):
        """09:30: one IP, one session, 15 small payments, all declined, in 90 s."""
        start = datetime.combine(self.day, datetime.min.time()) + timedelta(hours=9, minutes=30)
        ip = "91.121.87.45"
        for i in range(15):
            self.payment(start + timedelta(seconds=i * 6), "U-777", "S-FRAUD01", ip, "P-01",
                         rnd.randint(100, 200) / 100, "card", "declined")

    def fraud_velocity(self):
        """21:15: same user pays 3 high-value orders from 3 countries in 8 minutes."""
        start = datetime.combine(self.day, datetime.min.time()) + timedelta(hours=21, minutes=15)
        for i, prefix in enumerate(["41.226.10", "90.84.12", "98.137.4"]):
            self.payment(start + timedelta(minutes=i * 4), "U-666", "S-FRAUD02", random_ip(prefix),
                         rnd.choice(list(PRODUCTS)), rnd.randint(45000, 90000) / 100, "card", "success")

    def write(self, outdir):
        fid = "F-GEN-%s" % self.day.strftime("%Y%m%d")
        stamp = self.day.isoformat()
        files = {
            "csv": ("csv/%s__shop_%s.csv" % (fid, stamp), self._csv_text()),
            "json": ("json/%s__checkout_%s.json" % (fid, stamp), self._json_text()),
            "txt": ("txt/%s__gateway_%s.txt" % (fid, stamp), self._txt_text()),
        }
        for kind, (rel, text) in files.items():
            os.makedirs(os.path.join(outdir, kind), exist_ok=True)
            path = os.path.join(outdir, rel)
            with open(path + ".tmp", "w", newline="") as f:   # .tmp is ignored by Logstash
                f.write(text)
            os.replace(path + ".tmp", path)                   # appears complete, in one step
        return len(self.csv), len(self.json), len(self.txt)

    def _csv_text(self):
        import io
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        for _, row in sorted(self.csv, key=lambda x: x[0]):
            w.writerow(row)
        return buf.getvalue()

    def _json_text(self):
        return "".join(json.dumps(r) + "\n" for _, r in sorted(self.json, key=lambda x: x[0]))

    def _txt_text(self):
        return "".join(line + "\n" for _, line in sorted(self.txt, key=lambda x: x[0]))


def main():
    p = argparse.ArgumentParser(description="ShopFlow fake log generator")
    p.add_argument("--days", type=int, default=3, help="number of days (ending yesterday)")
    p.add_argument("--sessions", type=int, default=400, help="customer sessions per day")
    p.add_argument("--out", default="sample-data", help="output folder (csv/ json/ txt/ inside)")
    a = p.parse_args()

    last = date.today() - timedelta(days=1)
    for i in range(a.days):
        day = Day(last - timedelta(days=a.days - 1 - i))
        for n in range(a.sessions):
            day.session(n)
        extra = ""
        if i == a.days - 1:                      # story only on the last day
            day.incident()
            day.fraud_card_testing()
            day.fraud_velocity()
            extra = "  + incident 14:00 + 2 fraud patterns"
        c, j, t = day.write(a.out)
        print("%s  csv=%d json=%d txt=%d%s" % (day.day, c, j, t, extra))


if __name__ == "__main__":
    main()
