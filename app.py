"""
Operation Research Calculator - Web App (Versi Vercel)
Topik: Teori Antrean + Teori Transportasi + Teori Penugasan
"""
from flask import Flask, render_template, request, jsonify
import math
from itertools import permutations

app = Flask(__name__)


# ============================================================
# ============ BAGIAN 1: TEORI ANTREAN =======================
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
        "L": L, "Lq": Lq, "W": W, "Wq": Wq, "P_wait": rho,
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
    P0 = 1 / (K + 1) if abs(rho - 1) < 1e-9 else (1 - rho) / (1 - rho ** (K + 1))
    def Pn(n):
        if n > K: return 0.0
        if abs(rho - 1) < 1e-9: return 1 / (K + 1)
        return P0 * rho**n
    PK = Pn(K)
    lam_eff = lam * (1 - PK)
    L = K / 2 if abs(rho - 1) < 1e-9 else rho / (1 - rho) - (K + 1) * rho ** (K + 1) / (1 - rho ** (K + 1))
    Lq = L - (1 - P0)
    W = L / lam_eff if lam_eff > 0 else float("inf")
    Wq = Lq / lam_eff if lam_eff > 0 else float("inf")
    return {
        "model": f"M/M/1/{K}", "rho": rho, "P0": P0,
        "L": L, "Lq": Lq, "W": W, "Wq": Wq,
        "P_block": PK, "lambda_effective": lam_eff,
        "detail": {
            "Peluang sistem penuh (P_K)": PK,
            "Laju kedatangan efektif": lam_eff,
            "Pelanggan hilang per waktu": lam * PK,
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
            "Metode": "Pollaczek-Khinchine",
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


def interpretasi_antrean(res, lam, mu):
    rho, Lq, Wq, W = res["rho"], res["Lq"], res["Wq"], res["W"]
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
    if Wq < 0.05: tunggu = "hampir tidak ada antrean"
    elif Wq < 0.25: tunggu = "antrean singkat"
    elif Wq < 1: tunggu = "antrean sedang"
    elif Wq < 3: tunggu = "antrean panjang"
    else: tunggu = "antrean sangat panjang"
    return (f"Model {res['model']}. Sistem berada dalam kondisi {kondisi} dengan utilisasi "
            f"{rho*100:.1f}%. Rata-rata {Lq:.2f} pelanggan menunggu, tiap pelanggan menunggu "
            f"sekitar {Wq:.2f} satuan waktu. Total waktu di sistem {W:.2f}. Kondisi: {tunggu}. {saran}")


# ============================================================
# ============ BAGIAN 2: TEORI TRANSPORTASI =================
# ============================================================
def cek_keseimbangan(supply, demand):
    total_s = sum(supply)
    total_d = sum(demand)
    return total_s, total_d, abs(total_s - total_d) < 1e-9


def siapkan_matriks(cost, supply, demand):
    """Tambah baris/kolom dummy jika tidak seimbang."""
    supply = list(supply)
    demand = list(demand)
    cost = [row[:] for row in cost]
    total_s, total_d, balanced = cek_keseimbangan(supply, demand)

    if not balanced:
        if total_s > total_d:
            # tambah kolom dummy (demand)
            diff = total_s - total_d
            demand.append(diff)
            for row in cost:
                row.append(0)
        else:
            # tambah baris dummy (supply)
            diff = total_d - total_s
            supply.append(diff)
            cost.append([0] * len(demand))

    return cost, supply, demand, balanced


def north_west_corner(cost, supply, demand):
    supply = list(supply)
    demand = list(demand)
    m, n = len(supply), len(demand)
    alloc = [[0] * n for _ in range(m)]
    i = j = 0
    steps = []
    while i < m and j < n:
        qty = min(supply[i], demand[j])
        alloc[i][j] = qty
        steps.append({"from": f"S{i+1}", "to": f"D{j+1}", "qty": qty, "cost": cost[i][j]})
        supply[i] -= qty
        demand[j] -= qty
        if supply[i] == 0 and demand[j] == 0:
            i += 1; j += 1
        elif supply[i] == 0:
            i += 1
        else:
            j += 1
    return alloc, steps


def least_cost(cost, supply, demand):
    supply = list(supply)
    demand = list(demand)
    m, n = len(supply), len(demand)
    alloc = [[0] * n for _ in range(m)]
    steps = []
    while sum(supply) > 0 and sum(demand) > 0:
        # cari sel dengan biaya terkecil yang masih bisa dialokasikan
        best = None
        best_cost = float("inf")
        for i in range(m):
            if supply[i] == 0: continue
            for j in range(n):
                if demand[j] == 0: continue
                if cost[i][j] < best_cost:
                    best_cost = cost[i][j]
                    best = (i, j)
        if best is None:
            break
        i, j = best
        qty = min(supply[i], demand[j])
        alloc[i][j] = qty
        steps.append({"from": f"S{i+1}", "to": f"D{j+1}", "qty": qty, "cost": cost[i][j]})
        supply[i] -= qty
        demand[j] -= qty
    return alloc, steps


def vogel_approximation(cost, supply, demand):
    supply = list(supply)
    demand = list(demand)
    m, n = len(supply), len(demand)
    cost_work = [row[:] for row in cost]
    alloc = [[0] * n for _ in range(m)]
    steps = []
    active_rows = set(range(m))
    active_cols = set(range(n))
    while active_rows and active_cols:
        # hitung penalty per baris & kolom
        row_pen = {}
        for i in active_rows:
            vals = sorted([cost_work[i][j] for j in active_cols if demand[j] > 0])
            row_pen[i] = (vals[1] - vals[0]) if len(vals) >= 2 else (vals[0] if vals else 0)
        col_pen = {}
        for j in active_cols:
            vals = sorted([cost_work[i][j] for i in active_rows if supply[i] > 0])
            col_pen[j] = (vals[1] - vals[0]) if len(vals) >= 2 else (vals[0] if vals else 0)
        # cari penalty terbesar
        max_row = max(row_pen.items(), key=lambda x: x[1]) if row_pen else (None, -1)
        max_col = max(col_pen.items(), key=lambda x: x[1]) if col_pen else (None, -1)
        if max_row[1] >= max_col[1]:
            i = max_row[0]
            # pilih kolom dengan cost terkecil di baris i
            j = min([j for j in active_cols if demand[j] > 0],
                    key=lambda j: cost_work[i][j])
        else:
            j = max_col[0]
            i = min([i for i in active_rows if supply[i] > 0],
                    key=lambda i: cost_work[i][j])
        qty = min(supply[i], demand[j])
        alloc[i][j] = qty
        steps.append({"from": f"S{i+1}", "to": f"D{j+1}", "qty": qty, "cost": cost_work[i][j],
                      "row_pen": row_pen.get(i, 0), "col_pen": col_pen.get(j, 0)})
        supply[i] -= qty
        demand[j] -= qty
        if supply[i] == 0:
            active_rows.discard(i)
        if demand[j] == 0:
            active_cols.discard(j)
    return alloc, steps


def hitung_total_biaya(alloc, cost):
    total = 0
    rincian = []
    for i in range(len(alloc)):
        for j in range(len(alloc[i])):
            if alloc[i][j] > 0:
                sub = alloc[i][j] * cost[i][j]
                total += sub
                rincian.append({"from": f"S{i+1}", "to": f"D{j+1}",
                                "qty": alloc[i][j], "cost": cost[i][j], "subtotal": sub})
    return total, rincian


def hitung_optimum_modi(alloc, cost):
    """Implementasi MODI (u-v) untuk cek optimalitas sederhana.
       Return: status optimal + total cost."""
    m, n = len(alloc), len(alloc[0])
    total, _ = hitung_total_biaya(alloc, cost)
    # Bangun basis (sel > 0)
    basis = [(i, j) for i in range(m) for j in range(n) if alloc[i][j] > 0]
    if len(basis) < m + n - 1:
        # degenerate - perlu tambahan 0 untuk basis
        for i in range(m):
            for j in range(n):
                if (i, j) not in basis and len(basis) < m + n - 1:
                    basis.append((i, j))
                    break
            if len(basis) >= m + n - 1:
                break
    # Hitung u, v
    u = [None] * m
    v = [None] * n
    u[0] = 0
    changed = True
    while changed:
        changed = False
        for (i, j) in basis:
            if u[i] is not None and v[j] is None:
                v[j] = cost[i][j] - u[i]
                changed = True
            elif v[j] is not None and u[i] is None:
                u[i] = cost[i][j] - v[j]
                changed = True
    # Cek opportunity cost
    optimal = True
    for i in range(m):
        for j in range(n):
            if (i, j) not in basis and u[i] is not None and v[j] is not None:
                if cost[i][j] - (u[i] + v[j]) < 0:
                    optimal = False
                    break
        if not optimal:
            break
    return optimal, total


def interpretasi_transportasi(total_cost, rincian, metode, balanced, total_s, total_d):
    teks = (f"Metode {metode} menghasilkan total biaya transportasi sebesar {total_cost:.2f}. ")
    if not balanced:
        teks += (f"Catatan: masalah tidak seimbang (supply total = {total_s}, demand total = {total_d}), "
                 f"sehingga ditambahkan baris/kolom dummy dengan biaya 0. ")
    teks += (f"Alokasi optimal mengirim barang dari {len(set(r['from'] for r in rincian))} sumber "
             f"ke {len(set(r['to'] for r in rincian))} tujuan. ")
    teks += "Setiap baris rincian menunjukkan berapa unit dikirim dari sumber ke tujuan dan biayanya. "
    teks += "Semakin kecil total biaya, semakin efisien rencana transportasi Anda."
    return teks


# ============================================================
# ============ BAGIAN 3: TEORI PENUGASAN ====================
# ============================================================
def hungarian(cost_matrix):
    """Implementasi metode Hungarian untuk penugasan.
       Input: matriks biaya n×n. Return: assignment, total cost, steps."""
    n = len(cost_matrix)
    m = len(cost_matrix[0]) if cost_matrix else 0
    if n != m:
        return {"error": "Matriks penugasan harus persegi (jumlah baris = jumlah kolom). "
                         "Jika tidak persegi, tambahkan baris/kolom dummy dengan biaya 0."}

    # Step 1: kurangi minimum per baris
    C = [row[:] for row in cost_matrix]
    steps = []
    row_min = [min(row) for row in C]
    for i in range(n):
        for j in range(n):
            C[i][j] -= row_min[i]
    steps.append({"step": "1. Kurangi minimum tiap baris",
                  "matrix": [row[:] for row in C],
                  "min_per_row": row_min})

    # Step 2: kurangi minimum per kolom
    col_min = [min(C[i][j] for i in range(n)) for j in range(n)]
    for i in range(n):
        for j in range(n):
            C[i][j] -= col_min[j]
    steps.append({"step": "2. Kurangi minimum tiap kolom",
                  "matrix": [row[:] for row in C],
                  "min_per_col": col_min})

    # Step 3-6: iterasi penutupan garis
    max_iter = 50
    for iteration in range(max_iter):
        # Cari penugasan independen (matching)
        assignment = _find_assignment(C, n)
        if assignment is not None:
            total = sum(cost_matrix[i][assignment[i]] for i in range(n))
            return {
                "assignment": [{"task": f"Tugas {i+1}", "worker": f"Pekerja {assignment[i]+1}",
                                "cost": cost_matrix[i][assignment[i]]} for i in range(n)],
                "total_cost": total,
                "steps": steps,
                "matrix_reduced": [row[:] for row in C],
            }

        # Step 5: tutup nol dengan garis minimum
        covered_rows, covered_cols = _min_lines_cover_zeros(C, n)
        steps.append({"step": f"3. Tutup nol dengan garis minimum (iterasi {iteration+1})",
                      "matrix": [row[:] for row in C],
                      "covered_rows": covered_rows,
                      "covered_cols": covered_cols})

        # Step 6: cari nilai minimum yang tidak tertutup
        uncovered = [C[i][j] for i in range(n) for j in range(n)
                     if i not in covered_rows and j not in covered_cols]
        if not uncovered:
            return {"error": "Algoritma gagal: tidak ada nilai uncovered."}
        min_val = min(uncovered)
        # Kurangi semua uncovered, tambah di intersection
        for i in range(n):
            for j in range(n):
                if i in covered_rows and j in covered_cols:
                    C[i][j] += min_val
                elif i not in covered_rows and j not in covered_cols:
                    C[i][j] -= min_val
        steps.append({"step": f"4. Kurangi uncovered dengan {min_val}, tambah di intersection",
                      "matrix": [row[:] for row in C],
                      "min_val": min_val})

    return {"error": "Iterasi maksimum tercapai."}


def _find_assignment(C, n):
    """Cari matching sempurna menggunakan nol di matriks."""
    # Gunakan DFS augmenting path (Hungarian matching)
    match_col = [-1] * n
    def dfs(i, visited):
        for j in range(n):
            if C[i][j] == 0 and not visited[j]:
                visited[j] = True
                if match_col[j] == -1 or dfs(match_col[j], visited):
                    match_col[j] = i
                    return True
        return False
    count = 0
    for i in range(n):
        visited = [False] * n
        if dfs(i, visited):
            count += 1
    if count == n:
        assignment = [-1] * n
        for j in range(n):
            assignment[match_col[j]] = j
        return assignment
    return None


def _min_lines_cover_zeros(C, n):
    """Cari garis minimum untuk menutup semua nol.
       Return: covered_rows (set), covered_cols (set)."""
    # Simple greedy: tandai baris yang punya nol, dst. Cukup untuk demo.
    # Implementasi: gunakan matching maksimum untuk cari minimum vertex cover
    # Pendekatan sederhana: coba semua kombinasi (cocok untuk n kecil ≤ 10)
    # Untuk demo, kita pakai pendekatan heuristik: tutup semua baris dengan nol
    covered_rows = set()
    covered_cols = set()
    # Coba tutup semua baris dulu
    zero_positions = [(i, j) for i in range(n) for j in range(n) if C[i][j] == 0]
    # Tutup kolom dengan nol terbanyak
    col_count = {}
    for (i, j) in zero_positions:
        col_count[j] = col_count.get(j, 0) + 1
    covered_cols = set(sorted(col_count.keys(), key=lambda x: -col_count[x])[:max(1, len(col_count)-1)])
    # Baris yang masih punya nol uncovered, tutup
    for (i, j) in zero_positions:
        if j not in covered_cols:
            covered_rows.add(i)
    return covered_rows, covered_cols


def interpretasi_penugasan(total_cost, assignment):
    teks = (f"Total biaya penugasan optimal adalah {total_cost:.2f}. ")
    teks += (f"Setiap pekerja mendapat tepat satu tugas dan setiap tugas dikerjakan tepat satu pekerja. "
             f"Rincian: ")
    for a in assignment:
        teks += f"{a['worker']} → {a['task']} (biaya {a['cost']:.2f}); "
    teks = teks.rstrip("; ") + ". "
    teks += ("Penugasan ini adalah yang paling murah — tidak ada kombinasi lain yang menghasilkan "
             "total biaya lebih rendah. Metode Hungarian menjamin solusi optimal.")
    return teks


# ============================================================
# ============ ROUTE ========================================
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
            return jsonify({"error": "λ dan μ harus > 0."})
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
        res["interpretasi"] = interpretasi_antrean(res, lam, mu)
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
            rows.append({"model": name, "Lq": round(r["Lq"], 4),
                         "Wq": round(r["Wq"], 4), "W": round(r["W"], 4),
                         "rho": round(r["rho"], 4)})
        return jsonify({"rows": rows})
    except Exception as e:
        return jsonify({"error": str(e)})


# ----- Transportasi -----
@app.route("/api/transport", methods=["POST"])
def transport():
    try:
        data = request.get_json()
        cost = data.get("cost")       # list of list
        supply = data.get("supply")   # list
        demand = data.get("demand")   # list
        metode = data.get("metode", "nwc")  # nwc | least_cost | vam

        if not cost or not supply or not demand:
            return jsonify({"error": "Data biaya, supply, dan demand harus lengkap."})
        if len(cost) != len(supply):
            return jsonify({"error": "Jumlah baris biaya harus sama dengan jumlah supply."})
        if any(len(row) != len(demand) for row in cost):
            return jsonify({"error": "Setiap baris biaya harus sama panjang dengan jumlah demand."})

        total_s, total_d, balanced = cek_keseimbangan(supply, demand)
        cost2, supply2, demand2, _ = siapkan_matriks(cost, supply, demand)

        if metode == "nwc":
            alloc, steps = north_west_corner(cost2, supply2, demand2)
        elif metode == "least_cost":
            alloc, steps = least_cost(cost2, supply2, demand2)
        elif metode == "vam":
            alloc, steps = vogel_approximation(cost2, supply2, demand2)
        else:
            return jsonify({"error": "Metode tidak dikenal."})

        total, rincian = hitung_total_biaya(alloc, cost2)
        optimal, _ = hitung_optimum_modi(alloc, cost2)

        interpretasi = interpretasi_transportasi(total, rincian, metode.upper(),
                                                 balanced, total_s, total_d)
        if not optimal:
            interpretasi += (" Catatan: solusi ini belum tentu optimal. Gunakan metode MODI "
                             "atau Stepping Stone untuk perbaikan lebih lanjut.")

        return jsonify({
            "metode": metode.upper(),
            "balanced": balanced,
            "total_supply": total_s,
            "total_demand": total_d,
            "allocation": alloc,
            "steps": steps,
            "total_cost": total,
            "rincian": rincian,
            "optimal": optimal,
            "interpretasi": interpretasi,
            "cost_matrix_used": cost2,
            "supply_used": supply2,
            "demand_used": demand2,
        })
    except Exception as e:
        return jsonify({"error": f"Kesalahan: {str(e)}"})


# ----- Penugasan -----
@app.route("/api/assignment", methods=["POST"])
def assignment():
    try:
        data = request.get_json()
        cost = data.get("cost")
        if not cost or not all(isinstance(row, list) for row in cost):
            return jsonify({"error": "Matriks biaya harus berupa list of list."})
        n = len(cost)
        if n == 0:
            return jsonify({"error": "Matriks biaya kosong."})
        if any(len(row) != n for row in cost):
            return jsonify({"error": "Matriks harus persegi (n×n)."})

        res = hungarian(cost)
        if "error" in res:
            return jsonify(res)
        res["interpretasi"] = interpretasi_penugasan(res["total_cost"], res["assignment"])
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": f"Kesalahan: {str(e)}"})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)