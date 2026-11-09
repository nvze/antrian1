"""
Queueing Theory Calculator - Web App
Mendukung: M/M/1, M/M/c, M/M/1/K, M/G/1 (Pollaczek-Khinchine), M/D/1
"""

from flask import Flask, render_template, request, jsonify
import math

app = Flask(__name__)


# ============================================================
# MODEL M/M/1
# ============================================================
def mm1(lam, mu):
    if lam >= mu:
        return {"error": "Sistem tidak stabil: λ harus < μ"}
    rho = lam / mu
    L = rho / (1 - rho)
    Lq = rho**2 / (1 - rho)
    W = 1 / (mu - lam)
    Wq = rho / (mu - lam)
    P0 = 1 - rho
    Pn = lambda n: (1 - rho) * rho**n  # noqa: E731
    return {
        "model": "M/M/1",
        "rho": rho,
        "P0": P0,
        "L": L, "Lq": Lq, "W": W, "Wq": Wq,
        "P_system_empty": P0,
        "P_wait": rho,  # prob pelanggan harus menunggu
        "Pn_formula": f"Pn = (1 - ρ) ρ^n",
        "detail": {
            "P(n=0)": Pn(0), "P(n=1)": Pn(1),
            "P(n=2)": Pn(2), "P(n=3)": Pn(3),
            "P(n=5)": Pn(5), "P(n=10)": Pn(10),
        },
    }


# ============================================================
# MODEL M/M/c (multi-server)
# ============================================================
def mmc(lam, mu, c):
    if c < 1:
        return {"error": "Jumlah server c harus ≥ 1"}
    rho = lam / (c * mu)
    if rho >= 1:
        return {"error": f"Sistem tidak stabil: ρ = {rho:.4f} ≥ 1"}

    a = lam / mu  # offered load

    # P0
    sum_terms = sum(a**n / math.factorial(n) for n in range(c))
    last_term = (a**c / math.factorial(c)) * (1 / (1 - rho))
    P0 = 1 / (sum_terms + last_term)

    # Lq (Erlang C formula)
    Lq = (P0 * a**c * rho) / (math.factorial(c) * (1 - rho) ** 2)
    L = Lq + a
    Wq = Lq / lam
    W = Wq + 1 / mu

    # Probabilitas menunggu (Erlang C)
    Pw = (a**c / (math.factorial(c) * (1 - rho))) * P0

    # Utilisasi per server
    util_per_server = lam / (c * mu)

    return {
        "model": f"M/M/{c}",
        "rho": rho,
        "P0": P0,
        "L": L, "Lq": Lq, "W": W, "Wq": Wq,
        "P_wait": Pw,
        "offered_load_a": a,
        "utilization_per_server": util_per_server,
        "avg_busy_servers": a,
        "detail": {
            "Erlang_C (P_wait)": Pw,
            "Avg server sibuk": a,
            "Faktor utilisasi": util_per_server,
        },
    }


# ============================================================
# MODEL M/M/1/K (kapasitas terbatas)
# ============================================================
def mm1k(lam, mu, K):
    if K < 1:
        return {"error": "Kapasitas K harus ≥ 1"}
    rho = lam / mu
    if abs(rho - 1) < 1e-9:
        P0 = 1 / (K + 1)
    else:
        P0 = (1 - rho) / (1 - rho ** (K + 1))

    def Pn(n):
        if n > K:
            return 0.0
        if abs(rho - 1) < 1e-9:
            return 1 / (K + 1)
        return P0 * rho**n

    PK = Pn(K)  # prob sistem penuh
    lam_eff = lam * (1 - PK)  # laju kedatangan efektif

    if abs(rho - 1) < 1e-9:
        L = K / 2
    else:
        L = rho / (1 - rho) - (K + 1) * rho ** (K + 1) / (1 - rho ** (K + 1))

    Lq = L - (1 - P0)
    W = L / lam_eff if lam_eff > 0 else float("inf")
    Wq = Lq / lam_eff if lam_eff > 0 else float("inf")

    return {
        "model": f"M/M/1/{K}",
        "rho": rho,
        "P0": P0,
        "L": L, "Lq": Lq, "W": W, "Wq": Wq,
        "P_block": PK,
        "lambda_effective": lam_eff,
        "detail": {
            "Prob sistem penuh (P_K)": PK,
            "λ efektif (yang masuk)": lam_eff,
            "λ hilang (balking)": lam * PK,
        },
    }


# ============================================================
# MODEL M/G/1 (Pollaczek-Khinchine)
# ============================================================
def mg1(lam, mu, sigma):
    """sigma = standar deviasi waktu pelayanan"""
    if lam >= mu:
        return {"error": "Sistem tidak stabil: λ harus < μ"}
    rho = lam / mu
    # E[S] = 1/mu, E[S^2] = Var + E[S]^2 = sigma^2 + (1/mu)^2
    ES = 1 / mu
    ES2 = sigma**2 + ES**2
    Lq = (lam**2 * ES2) / (2 * (1 - rho))
    Wq = Lq / lam
    L = Lq + rho
    W = Wq + ES
    P0 = 1 - rho

    return {
        "model": "M/G/1",
        "rho": rho,
        "P0": P0,
        "L": L, "Lq": Lq, "W": W, "Wq": Wq,
        "E_S": ES, "E_S2": ES2,
        "detail": {
            "E[S] (rata-rata servis)": ES,
            "E[S²] (momen kedua)": ES2,
            "σ pelayanan": sigma,
            "Catatan": "Rumus Pollaczek-Khinchine",
        },
    }


# ============================================================
# MODEL M/D/1 (deterministik, variasi M/G/1)
# ============================================================
def md1(lam, mu):
    if lam >= mu:
        return {"error": "Sistem tidak stabil: λ harus < μ"}
    rho = lam / mu
    Lq = rho**2 / (2 * (1 - rho))
    Wq = Lq / lam
    L = Lq + rho
    W = Wq + 1 / mu
    P0 = 1 - rho

    return {
        "model": "M/D/1",
        "rho": rho,
        "P0": P0,
        "L": L, "Lq": Lq, "W": W, "Wq": Wq,
        "detail": {
            "Catatan": "Waktu layanan konstan (σ = 0)",
            "Perbandingan M/M/1": "Lq M/D/1 = ½ × Lq M/M/1",
        },
    }


# ============================================================
# ANALISIS BIAYA
# ============================================================
def cost_analysis(result, c_wait, c_server):
    """Total cost = Cw*L + Cs*c (c = jumlah server)"""
    c = int(result["model"].split("/")[-1]) if "/" in result["model"] else 1
    if "M/M/1" in result["model"] and "K" not in result["model"]:
        c = 1
    wait_cost = c_wait * result["L"]
    server_cost = c_server * c
    return {
        "waiting_cost": wait_cost,
        "server_cost": server_cost,
        "total_cost": wait_cost + server_cost,
        "c_wait": c_wait,
        "c_server": c_server,
        "num_servers": c,
    }


# ============================================================
# ROUTE
# ============================================================
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/calculate", methods=["POST"])
def calculate():
    try:
        data = request.get_json()
        model = data.get("model", "mm1")
        lam = float(data.get("lam", 0))
        mu = float(data.get("mu", 0))

        if lam <= 0 or mu <= 0:
            return jsonify({"error": "λ dan μ harus > 0"})

        if model == "mm1":
            res = mm1(lam, mu)
        elif model == "mmc":
            c = int(data.get("c", 2))
            res = mmc(lam, mu, c)
        elif model == "mm1k":
            K = int(data.get("K", 5))
            res = mm1k(lam, mu, K)
        elif model == "mg1":
            sigma = float(data.get("sigma", 1 / mu))
            res = mg1(lam, mu, sigma)
        elif model == "md1":
            res = md1(lam, mu)
        else:
            return jsonify({"error": "Model tidak dikenal"})

        if "error" in res:
            return jsonify(res)

        # Analisis biaya opsional
        c_wait = data.get("c_wait")
        c_server = data.get("c_server")
        if c_wait and c_server:
            try:
                res["cost"] = cost_analysis(
                    res, float(c_wait), float(c_server)
                )
            except Exception:
                pass

        return jsonify(res)
    except Exception as e:
        return jsonify({"error": f"Terjadi kesalahan: {str(e)}"})


@app.route("/api/compare", methods=["POST"])
def compare():
    """Bandingkan M/M/1 vs M/D/1 vs M/G/1 pada λ, μ yang sama."""
    try:
        data = request.get_json()
        lam = float(data["lam"])
        mu = float(data["mu"])
        sigma = float(data.get("sigma", 1 / mu))

        rows = []
        for name, fn in [
            ("M/M/1", lambda: mm1(lam, mu)),
            ("M/D/1", lambda: md1(lam, mu)),
            ("M/G/1", lambda: mg1(lam, mu, sigma)),
        ]:
            r = fn()
            if "error" in r:
                return jsonify(r)
            rows.append({
                "model": name,
                "Lq": round(r["Lq"], 4),
                "Wq": round(r["Wq"], 4),
                "W": round(r["W"], 4),
                "rho": round(r["rho"], 4),
            })
        return jsonify({"rows": rows})
    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
