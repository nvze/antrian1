"""
Queueing Theory Calculator - Web App (Versi Vercel + Edukasi)
Mendukung: M/M/1, M/M/c, M/M/1/K, M/G/1, M/D/1
"""
from flask import Flask, render_template, request, jsonify
import math

app = Flask(__name__)


# ============================================================
# MODEL MATEMATIKA
# ============================================================
def mm1(lam, mu):
    if lam >= mu:
        return {"error": "Sistem tidak stabil: laju kedatangan (λ) harus lebih kecil dari laju pelayanan (μ). Jika tidak, antrean akan terus tumbuh tanpa batas."}
    rho = lam / mu
    L = rho / (1 - rho)
    Lq = rho**2 / (1 - rho)
    W = 1 / (mu - lam)
    Wq = rho / (mu - lam)
    P0 = 1 - rho
    Pn = lambda n: (1 - rho) * rho**n
    return {
        "model": "M/M/1", "rho": rho, "P0": P0,
        "L": L, "Lq": Lq, "W": W, "Wq": Wq,
        "P_wait": rho,
        "detail": {
            "Peluang sistem kosong P(0)": Pn(0),
            "Peluang ada 1 pelanggan P(1)": Pn(1),
            "Peluang ada 2 pelanggan P(2)": Pn(2),
            "Peluang ada 3 pelanggan P(3)": Pn(3),
            "Peluang ada 5 pelanggan P(5)": Pn(5),
            "Peluang ada 10 pelanggan P(10)": Pn(10),
        },
    }


def mmc(lam, mu, c):
    if c < 1:
        return {"error": "Jumlah server (c) minimal 1."}
    rho = lam / (c * mu)
    if rho >= 1:
        return {"error": f"Sistem tidak stabil: utilisasi (ρ) = {rho:.4f} ≥ 1. Tambah jumlah server atau kurangi laju kedatangan."}
    a = lam / mu
    sum_terms = sum(a**n / math.factorial(n) for n in range(c))
    last_term = (a**c / math.factorial(c)) * (1 / (1 - rho))
    P0 = 1 / (sum_terms + last_term)
    Lq = (P0 * a**c * rho) / (math.factorial(c) * (1 - rho) ** 2)
    L = Lq + a
    Wq = Lq / lam
    W = Wq + 1 / mu
    Pw = (a**c / (math.factorial(c) * (1 - rho))) * P0
    return {
        "model": f"M/M/{c}", "rho": rho, "P0": P0,
        "L": L, "Lq": Lq, "W": W, "Wq": Wq, "P_wait": Pw,
        "detail": {
            "Erlang-C (peluang menunggu)": Pw,
            "Rata-rata server sibuk": a,
            "Utilisasi per server": rho,
        },
    }


def mm1k(lam, mu, K):
    if K < 1:
        return {"error": "Kapasitas sistem (K) minimal 1."}
    rho = lam / mu
    if abs(rho - 1) < 1e-9:
        P0 = 1 / (K + 1)
    else:
        P0 = (1 - rho) / (1 - rho ** (K + 1))
    def Pn(n):
        if n > K: return 0.0
        if abs(rho - 1) < 1e-9: return 1 / (K + 1)
        return P0 * rho**n
    PK = Pn(K)
    lam_eff = lam * (1 - PK)
    if abs(rho - 1) < 1e-9:
        L = K / 2
    else:
        L = rho / (1 - rho) - (K + 1) * rho ** (K + 1) / (1 - rho ** (K + 1))
    Lq = L - (1 - P0)
    W = L / lam_eff if lam_eff > 0 else float("inf")
    Wq = Lq / lam_eff if lam_eff > 0 else float("inf")
    return {
        "model": f"M/M/1/{K}", "rho": rho, "P0": P0,
        "L": L, "Lq": Lq, "W": W, "Wq": Wq,
        "P_block": PK, "lambda_effective": lam_eff,
        "detail": {
            "Peluang sistem penuh (P_K)": PK,
            "Laju kedatangan efektif (λ_eff)": lam_eff,
            "Pelanggan hilang (balking) per waktu": lam * PK,
        },
    }


def mg1(lam, mu, sigma):
    if lam >= mu:
        return {"error": "Sistem tidak stabil: λ harus < μ."}
    rho = lam / mu
    ES = 1 / mu
    ES2 = sigma**2 + ES**2
    Lq = (lam**2 * ES2) / (2 * (1 - rho))
    Wq = Lq / lam
    L = Lq + rho
    W = Wq + ES
    return {
        "model": "M/G/1", "rho": rho, "P0": 1 - rho,
        "L": L, "Lq": Lq, "W": W, "Wq": Wq,
        "detail": {
            "Rata-rata waktu layanan E[S]": ES,
            "Momen kedua E[S²]": ES2,
            "Standar deviasi layanan (σ)": sigma,
            "Metode": "Rumus Pollaczek-Khinchine",
        },
    }


def md1(lam, mu):
    if lam >= mu:
        return {"error": "Sistem tidak stabil: λ harus < μ."}
    rho = lam / mu
    Lq = rho**2 / (2 * (1 - rho))
    Wq = Lq / lam
    L = Lq + rho
    W = Wq + 1 / mu
    return {
        "model": "M/D/1", "rho": rho, "P0": 1 - rho,
        "L": L, "Lq": Lq, "W": W, "Wq": Wq,
        "detail": {
            "Catatan": "Waktu layanan konstan (σ = 0)",
            "Keunggulan": "Lq hanya setengah dari M/M/1",
        },
    }


def cost_analysis(result, c_wait, c_server):
    model = result["model"]
    c = 1
    if model.startswith("M/M/") and "/K" not in model and model != "M/M/1":
        try:
            c = int(model.split("/")[-1])
        except:
            c = 1
    wait_cost = c_wait * result["L"]
    server_cost = c_server * c
    return {
        "waiting_cost": wait_cost, "server_cost": server_cost,
        "total_cost": wait_cost + server_cost,
        "c_wait": c_wait, "c_server": c_server, "num_servers": c,
    }


# ============================================================
# INTERPRETASI BAHASA MANUSIA (untuk orang awam)
# ============================================================
def interpretasi(res, lam, mu):
    rho = res["rho"]
    Lq = res["Lq"]
    Wq = res["Wq"]
    W = res["W"]
    model = res["model"]

    # Kategori utilisasi
    if rho < 0.5:
        kondisi = "sangat longgar"
        saran = "Sistem Anda masih sangat santai. Ada banyak waktu menganggur. Anda mungkin bisa mengurangi jumlah server atau menggabungkan dengan tugas lain untuk menghemat biaya."
    elif rho < 0.7:
        kondisi = "nyaman"
        saran = "Sistem berjalan nyaman. Pelanggan jarang menunggu lama. Ini kondisi ideal untuk sebagian besar layanan."
    elif rho < 0.85:
        kondisi = "cukup sibuk"
        saran = "Sistem cukup sibuk tapi masih terkendali. Pantau terus agar tidak naik melewati 85%."
    elif rho < 0.95:
        kondisi = "sangat sibuk"
        saran = "Sistem sangat sibuk. Sedikit gangguan saja bisa membuat antrean meledak. Pertimbangkan menambah kapasitas."
    else:
        kondisi = "kritis"
        saran = "Sistem berada di ambang batas. Antrean bisa meledak kapan saja. Sangat disarankan menambah server atau mengurangi laju kedatangan."

    # Kategori waktu tunggu
    if Wq < 0.05:
        tunggu = "hampir tidak ada antrean"
    elif Wq < 0.25:
        tunggu = "antrean singkat"
    elif Wq < 1:
        tunggu = "antrean sedang"
    elif Wq < 3:
        tunggu = "antrean panjang"
    else:
        tunggu = "antrean sangat panjang"

    teks = (
        f"Model yang Anda pilih adalah {model}. Berdasarkan perhitungan, sistem Anda berada dalam kondisi "
        f"{kondisi} dengan tingkat utilisasi {rho*100:.1f}% (artinya server sibuk sekitar {rho*100:.0f}% dari waktu). "
        f"Rata-rata ada {Lq:.2f} pelanggan yang sedang menunggu dalam antrean, dan setiap pelanggan harus menunggu "
        f"sekitar {Wq:.2f} satuan waktu sebelum dilayani. Total waktu yang dihabiskan pelanggan di sistem "
        f"(menunggu + dilayani) sekitar {W:.2f} satuan waktu. Kondisi ini tergolong {tunggu}. {saran}"
    )
    return teks


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
            return jsonify({"error": "λ dan μ harus lebih besar dari 0."})

        if model == "mm1":
            res = mm1(lam, mu)
        elif model == "mmc":
            res = mmc(lam, mu, int(data.get("c", 2)))
        elif model == "mm1k":
            res = mm1k(lam, mu, int(data.get("K", 5)))
        elif model == "mg1":
            res = mg1(lam, mu, float(data.get("sigma", 1 / mu)))
        elif model == "md1":
            res = md1(lam, mu)
        else:
            return jsonify({"error": "Model tidak dikenal."})

        if "error" in res:
            return jsonify(res)

        # Tambahkan interpretasi bahasa manusia
        res["interpretasi"] = interpretasi(res, lam, mu)

        cw, cs = data.get("c_wait"), data.get("c_server")
        if cw and cs:
            try:
                res["cost"] = cost_analysis(res, float(cw), float(cs))
            except Exception:
                pass
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": f"Kesalahan: {str(e)}"})


@app.route("/api/compare", methods=["POST"])
def compare():
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
                "model": name, "Lq": round(r["Lq"], 4),
                "Wq": round(r["Wq"], 4), "W": round(r["W"], 4),
                "rho": round(r["rho"], 4),
            })
        return jsonify({"rows": rows})
    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)