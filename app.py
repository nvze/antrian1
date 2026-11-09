"""
Operation Research Calculator - Web App (Versi Vercel)
Topik: Antrean + Transportasi + Penugasan + CPM + PERT
"""
from flask import Flask, render_template, request, jsonify
import math

app = Flask(__name__)


# ============================================================
# ============ BAGIAN 1: TEORI ANTREAN =======================
# ============================================================
def mm1(lam, mu):
    if lam >= mu:
        return {"error": "Sistem tidak stabil: lambda harus < mu."}
    rho = lam / mu
    L = rho / (1 - rho)
    Lq = rho**2 / (1 - rho)
    W = 1 / (mu - lam)
    Wq = rho / (mu - lam)
    P0 = 1 - rho
    Pn = lambda n: (1 - rho) * rho**n
    return {"model": "M/M/1", "rho": rho, "P0": P0, "L": L, "Lq": Lq,
            "W": W, "Wq": Wq, "P_wait": rho,
            "detail": {"Peluang sistem kosong P(0)": Pn(0),
                       "Peluang ada 1 pelanggan P(1)": Pn(1),
                       "Peluang ada 2 pelanggan P(2)": Pn(2),
                       "Peluang ada 3 pelanggan P(3)": Pn(3),
                       "Peluang ada 5 pelanggan P(5)": Pn(5),
                       "Peluang ada 10 pelanggan P(10)": Pn(10)}}


def mmc(lam, mu, c):
    if c < 1: return {"error": "Jumlah server c minimal 1."}
    rho = lam / (c * mu)
    if rho >= 1:
        return {"error": f"Sistem tidak stabil: rho = {rho:.4f} >= 1."}
    a = lam / mu
    sum_terms = sum(a**n / math.factorial(n) for n in range(c))
    last_term = (a**c / math.factorial(c)) * (1 / (1 - rho))
    P0 = 1 / (sum_terms + last_term)
    Lq = (P0 * a**c * rho) / (math.factorial(c) * (1 - rho) ** 2)
    L = Lq + a; Wq = Lq / lam; W = Wq + 1 / mu
    Pw = (a**c / (math.factorial(c) * (1 - rho))) * P0
    return {"model": f"M/M/{c}", "rho": rho, "P0": P0, "L": L, "Lq": Lq,
            "W": W, "Wq": Wq, "P_wait": Pw,
            "detail": {"Erlang-C (peluang menunggu)": Pw,
                       "Rata-rata server sibuk": a,
                       "Utilisasi per server": rho}}


def mm1k(lam, mu, K):
    if K < 1: return {"error": "Kapasitas K minimal 1."}
    rho = lam / mu
    P0 = 1 / (K + 1) if abs(rho - 1) < 1e-9 else (1 - rho) / (1 - rho ** (K + 1))
    def Pn(n):
        if n > K: return 0.0
        if abs(rho - 1) < 1e-9: return 1 / (K + 1)
        return P0 * rho**n
    PK = Pn(K); lam_eff = lam * (1 - PK)
    L = K / 2 if abs(rho - 1) < 1e-9 else rho / (1 - rho) - (K + 1) * rho ** (K + 1) / (1 - rho ** (K + 1))
    Lq = L - (1 - P0)
    W = L / lam_eff if lam_eff > 0 else float("inf")
    Wq = Lq / lam_eff if lam_eff > 0 else float("inf")
    return {"model": f"M/M/1/{K}", "rho": rho, "P0": P0, "L": L, "Lq": Lq,
            "W": W, "Wq": Wq, "P_block": PK, "lambda_effective": lam_eff,
            "detail": {"Peluang sistem penuh P_K": PK,
                       "Laju kedatangan efektif": lam_eff,
                       "Pelanggan hilang per waktu": lam * PK}}


def mg1(lam, mu, sigma):
    if lam >= mu: return {"error": "Sistem tidak stabil."}
    rho = lam / mu; ES = 1 / mu; ES2 = sigma**2 + ES**2
    Lq = (lam**2 * ES2) / (2 * (1 - rho))
    Wq = Lq / lam; L = Lq + rho; W = Wq + ES
    return {"model": "M/G/1", "rho": rho, "P0": 1 - rho, "L": L, "Lq": Lq,
            "W": W, "Wq": Wq,
            "detail": {"Rata-rata waktu layanan E[S]": ES,
                       "Momen kedua E[S^2]": ES2,
                       "Standar deviasi sigma": sigma,
                       "Metode": "Pollaczek-Khinchine"}}


def md1(lam, mu):
    if lam >= mu: return {"error": "Sistem tidak stabil."}
    rho = lam / mu
    Lq = rho**2 / (2 * (1 - rho))
    Wq = Lq / lam; L = Lq + rho; W = Wq + 1 / mu
    return {"model": "M/D/1", "rho": rho, "P0": 1 - rho, "L": L, "Lq": Lq,
            "W": W, "Wq": Wq,
            "detail": {"Catatan": "Waktu layanan konstan (sigma = 0)",
                       "Keunggulan": "Lq setengah dari M/M/1"}}


def cost_analysis(result, c_wait, c_server):
    model = result["model"]; c = 1
    if model.startswith("M/M/") and "/K" not in model and model != "M/M/1":
        try: c = int(model.split("/")[-1])
        except: c = 1
    wait_cost = c_wait * result["L"]; server_cost = c_server * c
    return {"waiting_cost": wait_cost, "server_cost": server_cost,
            "total_cost": wait_cost + server_cost,
            "c_wait": c_wait, "c_server": c_server, "num_servers": c}


def interpretasi_antrean(res, lam, mu):
    rho, Lq, Wq, W = res["rho"], res["Lq"], res["Wq"], res["W"]
    if rho < 0.5: kondisi, saran = "sangat longgar", "Sistem sangat santai. Bisa kurangi server."
    elif rho < 0.7: kondisi, saran = "nyaman", "Sistem ideal. Pelanggan jarang menunggu."
    elif rho < 0.85: kondisi, saran = "cukup sibuk", "Pantau agar tidak naik melewati 85%."
    elif rho < 0.95: kondisi, saran = "sangat sibuk", "Pertimbangkan menambah kapasitas."
    else: kondisi, saran = "kritis", "Antrean bisa meledak kapan saja. Tambah server!"
    if Wq < 0.05: tunggu = "hampir tidak ada antrean"
    elif Wq < 0.25: tunggu = "antrean singkat"
    elif Wq < 1: tunggu = "antrean sedang"
    elif Wq < 3: tunggu = "antrean panjang"
    else: tunggu = "antrean sangat panjang"
    return (f"Model {res['model']}. Kondisi {kondisi} dengan utilisasi {rho*100:.1f}%. "
            f"Rata-rata {Lq:.2f} pelanggan menunggu, tiap pelanggan menunggu {Wq:.2f} satuan waktu. "
            f"Total waktu di sistem {W:.2f}. {tunggu}. {saran}")


# ============================================================
# ============ BAGIAN 2: TEORI TRANSPORTASI =================
# ============================================================
def cek_keseimbangan(supply, demand):
    total_s = sum(supply); total_d = sum(demand)
    return total_s, total_d, abs(total_s - total_d) < 1e-9


def siapkan_matriks(cost, supply, demand):
    supply = list(supply); demand = list(demand); cost = [row[:] for row in cost]
    total_s, total_d, balanced = cek_keseimbangan(supply, demand)
    if not balanced:
        if total_s > total_d:
            diff = total_s - total_d; demand.append(diff)
            for row in cost: row.append(0)
        else:
            diff = total_d - total_s; supply.append(diff)
            cost.append([0] * len(demand))
    return cost, supply, demand, balanced


def north_west_corner(cost, supply, demand):
    supply = list(supply); demand = list(demand)
    m, n = len(supply), len(demand)
    alloc = [[0] * n for _ in range(m)]; steps = []; i = j = 0
    while i < m and j < n:
        qty = min(supply[i], demand[j]); alloc[i][j] = qty
        steps.append({"from": f"S{i+1}", "to": f"D{j+1}", "qty": qty, "cost": cost[i][j]})
        supply[i] -= qty; demand[j] -= qty
        if supply[i] == 0 and demand[j] == 0: i += 1; j += 1
        elif supply[i] == 0: i += 1
        else: j += 1
    return alloc, steps


def least_cost(cost, supply, demand):
    supply = list(supply); demand = list(demand)
    m, n = len(supply), len(demand)
    alloc = [[0] * n for _ in range(m)]; steps = []
    while sum(supply) > 0 and sum(demand) > 0:
        best = None; best_cost = float("inf")
        for i in range(m):
            if supply[i] == 0: continue
            for j in range(n):
                if demand[j] == 0: continue
                if cost[i][j] < best_cost: best_cost = cost[i][j]; best = (i, j)
        if best is None: break
        i, j = best; qty = min(supply[i], demand[j]); alloc[i][j] = qty
        steps.append({"from": f"S{i+1}", "to": f"D{j+1}", "qty": qty, "cost": cost[i][j]})
        supply[i] -= qty; demand[j] -= qty
    return alloc, steps


def vogel_approximation(cost, supply, demand):
    supply = list(supply); demand = list(demand)
    m, n = len(supply), len(demand)
    cost_work = [row[:] for row in cost]; alloc = [[0] * n for _ in range(m)]
    steps = []; active_rows = set(range(m)); active_cols = set(range(n))
    while active_rows and active_cols:
        row_pen = {}
        for i in active_rows:
            vals = sorted([cost_work[i][j] for j in active_cols if demand[j] > 0])
            row_pen[i] = (vals[1] - vals[0]) if len(vals) >= 2 else (vals[0] if vals else 0)
        col_pen = {}
        for j in active_cols:
            vals = sorted([cost_work[i][j] for i in active_rows if supply[i] > 0])
            col_pen[j] = (vals[1] - vals[0]) if len(vals) >= 2 else (vals[0] if vals else 0)
        max_row = max(row_pen.items(), key=lambda x: x[1]) if row_pen else (None, -1)
        max_col = max(col_pen.items(), key=lambda x: x[1]) if col_pen else (None, -1)
        if max_row[1] >= max_col[1]:
            i = max_row[0]
            j = min([j for j in active_cols if demand[j] > 0], key=lambda j: cost_work[i][j])
        else:
            j = max_col[0]
            i = min([i for i in active_rows if supply[i] > 0], key=lambda i: cost_work[i][j])
        qty = min(supply[i], demand[j]); alloc[i][j] = qty
        steps.append({"from": f"S{i+1}", "to": f"D{j+1}", "qty": qty, "cost": cost_work[i][j]})
        supply[i] -= qty; demand[j] -= qty
        if supply[i] == 0: active_rows.discard(i)
        if demand[j] == 0: active_cols.discard(j)
    return alloc, steps


def hitung_total_biaya(alloc, cost):
    total = 0; rincian = []
    for i in range(len(alloc)):
        for j in range(len(alloc[i])):
            if alloc[i][j] > 0:
                sub = alloc[i][j] * cost[i][j]; total += sub
                rincian.append({"from": f"S{i+1}", "to": f"D{j+1}",
                                "qty": alloc[i][j], "cost": cost[i][j], "subtotal": sub})
    return total, rincian


def hitung_optimum_modi(alloc, cost):
    m, n = len(alloc), len(alloc[0])
    total, _ = hitung_total_biaya(alloc, cost)
    basis = [(i, j) for i in range(m) for j in range(n) if alloc[i][j] > 0]
    if len(basis) < m + n - 1:
        for i in range(m):
            for j in range(n):
                if (i, j) not in basis and len(basis) < m + n - 1:
                    basis.append((i, j))
            if len(basis) >= m + n - 1: break
    u = [None] * m; v = [None] * n; u[0] = 0; changed = True
    while changed:
        changed = False
        for (i, j) in basis:
            if u[i] is not None and v[j] is None: v[j] = cost[i][j] - u[i]; changed = True
            elif v[j] is not None and u[i] is None: u[i] = cost[i][j] - v[j]; changed = True
    optimal = True
    for i in range(m):
        for j in range(n):
            if (i, j) not in basis and u[i] is not None and v[j] is not None:
                if cost[i][j] - (u[i] + v[j]) < 0: optimal = False; break
        if not optimal: break
    return optimal, total


def interpretasi_transportasi(total_cost, rincian, metode, balanced, total_s, total_d):
    teks = f"Metode {metode} menghasilkan total biaya {total_cost:.2f}. "
    if not balanced:
        teks += f"Masalah tidak seimbang (supply={total_s}, demand={total_d}), ditambahkan dummy. "
    teks += (f"Alokasi mengirim dari {len(set(r['from'] for r in rincian))} sumber ke "
             f"{len(set(r['to'] for r in rincian))} tujuan. Semakin kecil total biaya, semakin efisien.")
    return teks


# ============================================================
# ============ BAGIAN 3: TEORI PENUGASAN ====================
# ============================================================
def hungarian(cost_matrix):
    n = len(cost_matrix)
    m = len(cost_matrix[0]) if cost_matrix else 0
    if n != m:
        return {"error": "Matriks harus persegi (n x n)."}
    C = [row[:] for row in cost_matrix]; steps = []
    row_min = [min(row) for row in C]
    for i in range(n):
        for j in range(n): C[i][j] -= row_min[i]
    steps.append({"step": "1. Kurangi minimum tiap baris", "matrix": [row[:] for row in C]})
    col_min = [min(C[i][j] for i in range(n)) for j in range(n)]
    for i in range(n):
        for j in range(n): C[i][j] -= col_min[j]
    steps.append({"step": "2. Kurangi minimum tiap kolom", "matrix": [row[:] for row in C]})
    for iteration in range(50):
        assignment = _find_assignment(C, n)
        if assignment is not None:
            total = sum(cost_matrix[i][assignment[i]] for i in range(n))
            return {"assignment": [{"task": f"Tugas {i+1}", "worker": f"Pekerja {assignment[i]+1}",
                                    "cost": cost_matrix[i][assignment[i]]} for i in range(n)],
                    "total_cost": total, "steps": steps}
        covered_rows, covered_cols = _min_lines_cover_zeros(C, n)
        steps.append({"step": f"3. Tutup nol dengan garis minimum (iterasi {iteration+1})",
                      "matrix": [row[:] for row in C]})
        uncovered = [C[i][j] for i in range(n) for j in range(n)
                     if i not in covered_rows and j not in covered_cols]
        if not uncovered: return {"error": "Algoritma gagal."}
        min_val = min(uncovered)
        for i in range(n):
            for j in range(n):
                if i in covered_rows and j in covered_cols: C[i][j] += min_val
                elif i not in covered_rows and j not in covered_cols: C[i][j] -= min_val
        steps.append({"step": f"4. Kurangi uncovered dengan {min_val}", "matrix": [row[:] for row in C]})
    return {"error": "Iterasi maksimum."}


def _find_assignment(C, n):
    match_col = [-1] * n
    def dfs(i, visited):
        for j in range(n):
            if C[i][j] == 0 and not visited[j]:
                visited[j] = True
                if match_col[j] == -1 or dfs(match_col[j], visited):
                    match_col[j] = i; return True
        return False
    count = 0
    for i in range(n):
        visited = [False] * n
        if dfs(i, visited): count += 1
    if count == n:
        assignment = [-1] * n
        for j in range(n): assignment[match_col[j]] = j
        return assignment
    return None


def _min_lines_cover_zeros(C, n):
    covered_rows = set(); covered_cols = set()
    zero_positions = [(i, j) for i in range(n) for j in range(n) if C[i][j] == 0]
    col_count = {}
    for (i, j) in zero_positions: col_count[j] = col_count.get(j, 0) + 1
    covered_cols = set(sorted(col_count.keys(), key=lambda x: -col_count[x])[:max(1, len(col_count)-1)])
    for (i, j) in zero_positions:
        if j not in covered_cols: covered_rows.add(i)
    return covered_rows, covered_cols


def interpretasi_penugasan(total_cost, assignment):
    teks = f"Total biaya penugasan optimal adalah {total_cost:.2f}. Rincian: "
    for a in assignment: teks += f"{a['worker']} -> {a['task']} ({a['cost']:.2f}); "
    teks = teks.rstrip("; ") + ". Metode Hungarian menjamin solusi optimal."
    return teks


# ============================================================
# ============ BAGIAN 4: CPM (Critical Path Method) ==========
# ============================================================
def hitung_cpm(activities):
    """
    activities: list of dict {id, name, duration, predecessors}
    Return: ES, EF, LS, LF, slack, critical path, project duration, steps
    """
    # Bangun graf
    act_dict = {a["id"]: a for a in activities}
    # Validasi predecessor ada
    for a in activities:
        for p in a["predecessors"]:
            if p not in act_dict:
                return {"error": f"Predecessor '{p}' untuk aktivitas '{a['id']}' tidak ditemukan."}
    # Deteksi cycle sederhana dengan topological sort
    # Hitung durasi & susun urutan
    n = len(activities)
    # Topological order
    in_degree = {a["id"]: 0 for a in activities}
    adj = {a["id"]: [] for a in activities}
    for a in activities:
        for p in a["predecessors"]:
            adj[p].append(a["id"])
            in_degree[a["id"]] += 1
    queue = [aid for aid, d in in_degree.items() if d == 0]
    topo = []
    while queue:
        u = queue.pop(0); topo.append(u)
        for v in adj[u]:
            in_degree[v] -= 1
            if in_degree[v] == 0: queue.append(v)
    if len(topo) != n:
        return {"error": "Terdeteksi siklus (cycle) pada dependency antar aktivitas. CPM hanya untuk DAG."}

    # Forward pass: ES, EF
    ES = {}; EF = {}
    for aid in topo:
        a = act_dict[aid]
        if not a["predecessors"]:
            ES[aid] = 0
        else:
            ES[aid] = max(EF[p] for p in a["predecessors"])
        EF[aid] = ES[aid] + a["duration"]

    # Project duration
    project_duration = max(EF.values()) if EF else 0

    # Backward pass: LS, LF
    LS = {}; LF = {}
    for aid in reversed(topo):
        a = act_dict[aid]
        successors = adj[aid]
        if not successors:
            LF[aid] = project_duration
        else:
            LF[aid] = min(LS[s] for s in successors)
        LS[aid] = LF[aid] - a["duration"]

    # Slack
    slack = {aid: LS[aid] - ES[aid] for aid in act_dict}

    # Critical path: aktivitas dengan slack 0
    critical = [aid for aid in act_dict if abs(slack[aid]) < 1e-9]

    # Susun urutan critical path (urut dari ES)
    critical_sorted = sorted(critical, key=lambda x: ES[x])

    # Bangun rincian per aktivitas
    rincian = []
    for a in activities:
        aid = a["id"]
        rincian.append({
            "id": aid, "name": a.get("name", aid), "duration": a["duration"],
            "predecessors": a["predecessors"],
            "ES": ES[aid], "EF": EF[aid], "LS": LS[aid], "LF": LF[aid],
            "slack": slack[aid],
            "critical": abs(slack[aid]) < 1e-9,
        })

    # Bangun langkah-langkah penjelasan
    steps = []
    steps.append({
        "step": "1. Forward Pass - Hitung Early Start (ES) dan Early Finish (EF)",
        "detail": "ES = max(EF predecessor). EF = ES + durasi. Mulai dari aktivitas tanpa predecessor."
    })
    for aid in topo:
        a = act_dict[aid]
        pred_str = ", ".join(a["predecessors"]) if a["predecessors"] else "(tidak ada)"
        steps.append({
            "step": f"  {aid} ({a.get('name', aid)}): ES={ES[aid]}, EF={EF[aid]}",
            "detail": f"Predecessor: {pred_str}. ES = {'max(EF pred)' if a['predecessors'] else '0'}, EF = ES + {a['duration']} = {EF[aid]}."
        })
    steps.append({
        "step": f"2. Durasi proyek = max(EF) = {project_duration}",
        "detail": "Waktu minimum yang dibutuhkan untuk menyelesaikan seluruh proyek."
    })
    steps.append({
        "step": "3. Backward Pass - Hitung Late Start (LS) dan Late Finish (LF)",
        "detail": "LF = min(LS successor). LS = LF - durasi. Mulai dari aktivitas tanpa successor."
    })
    for aid in reversed(topo):
        a = act_dict[aid]
        succ_str = ", ".join(adj[aid]) if adj[aid] else "(tidak ada)"
        steps.append({
            "step": f"  {aid}: LS={LS[aid]}, LF={LF[aid]}",
            "detail": f"Successor: {succ_str}. LF = {'min(LS succ)' if adj[aid] else 'durasi proyek'}, LS = LF - {a['duration']} = {LS[aid]}."
        })
    steps.append({
        "step": "4. Hitung Slack (kelonggaran) = LS - ES",
        "detail": "Slack = 0 berarti aktivitas kritis. Jika aktivitas ini terlambat, seluruh proyek ikut terlambat."
    })
    for a in activities:
        aid = a["id"]
        steps.append({
            "step": f"  {aid}: Slack = {LS[aid]} - {ES[aid]} = {slack[aid]}",
            "detail": "KRITIS" if abs(slack[aid]) < 1e-9 else "Tidak kritis (bisa ditunda)"
        })

    return {
        "activities": rincian,
        "project_duration": project_duration,
        "critical_path": critical_sorted,
        "steps": steps,
    }


def interpretasi_cpm(result):
    durasi = result["project_duration"]
    critical = result["critical_path"]
    n_crit = len(critical)
    n_total = len(result["activities"])
    non_crit = [a for a in result["activities"] if not a["critical"]]
    teks = (f"Proyek ini membutuhkan waktu minimum {durasi} satuan waktu. "
            f"Ada {n_crit} aktivitas kritis dari total {n_total} aktivitas. "
            f"Jalur kritis: {' -> '.join(critical)}. ")
    if non_crit:
        contoh = non_crit[0]
        teks += (f"Contoh aktivitas tidak kritis: {contoh['id']} (slack {contoh['slack']:.2f}), "
                 f"bisa ditunda hingga {contoh['slack']:.2f} satuan waktu tanpa memperlambat proyek. ")
    else:
        teks += "Semua aktivitas kritis — tidak ada yang bisa ditunda. "
    teks += ("Fokuslah memantau aktivitas kritis: jika salah satu terlambat, seluruh proyek ikut terlambat. "
             "Aktivitas non-kritis bisa dijadwalkan lebih fleksibel untuk menghemat biaya.")
    return teks


# ============================================================
# ============ BAGIAN 5: PERT (Program Evaluation and Review Technique) ==========
# ============================================================
def hitung_pert(activities):
    """
    activities: list of dict {id, name, optimistic, most_likely, pessimistic, predecessors}
    Return: expected duration, variance, ES, EF, critical path, probability
    """
    act_dict = {a["id"]: a for a in activities}
    # Validasi
    for a in activities:
        if a["optimistic"] > a["most_likely"] or a["most_likely"] > a["pessimistic"]:
            return {"error": f"Aktivitas '{a['id']}': harus memenuhi O <= M <= P."}
        for p in a["predecessors"]:
            if p not in act_dict:
                return {"error": f"Predecessor '{p}' tidak ditemukan."}

    # Hitung expected duration & variance untuk tiap aktivitas
    expected = {}
    variance = {}
    for a in activities:
        aid = a["id"]
        O, M, P = a["optimistic"], a["most_likely"], a["pessimistic"]
        te = (O + 4 * M + P) / 6
        var = ((P - O) / 6) ** 2
        expected[aid] = te
        variance[aid] = var

    # Topological order (sama seperti CPM)
    in_degree = {a["id"]: 0 for a in activities}
    adj = {a["id"]: [] for a in activities}
    for a in activities:
        for p in a["predecessors"]:
            adj[p].append(a["id"]); in_degree[a["id"]] += 1
    queue = [aid for aid, d in in_degree.items() if d == 0]
    topo = []
    while queue:
        u = queue.pop(0); topo.append(u)
        for v in adj[u]:
            in_degree[v] -= 1
            if in_degree[v] == 0: queue.append(v)
    if len(topo) != len(activities):
        return {"error": "Terdeteksi siklus pada dependency. PERT hanya untuk DAG."}

    # Forward pass dengan expected duration
    ES = {}; EF = {}
    for aid in topo:
        a = act_dict[aid]
        if not a["predecessors"]: ES[aid] = 0
        else: ES[aid] = max(EF[p] for p in a["predecessors"])
        EF[aid] = ES[aid] + expected[aid]

    project_duration = max(EF.values()) if EF else 0

    # Backward pass
    LS = {}; LF = {}
    for aid in reversed(topo):
        a = act_dict[aid]
        if not adj[aid]: LF[aid] = project_duration
        else: LF[aid] = min(LS[s] for s in adj[aid])
        LS[aid] = LF[aid] - expected[aid]

    slack = {aid: LS[aid] - ES[aid] for aid in act_dict}
    critical = [aid for aid in act_dict if abs(slack[aid]) < 1e-9]
    critical_sorted = sorted(critical, key=lambda x: ES[x])

    # Variance total proyek = sum variance aktivitas kritis
    project_variance = sum(variance[aid] for aid in critical)
    project_std = math.sqrt(project_variance)

    # Rincian per aktivitas
    rincian = []
    for a in activities:
        aid = a["id"]
        rincian.append({
            "id": aid, "name": a.get("name", aid),
            "O": a["optimistic"], "M": a["most_likely"], "P": a["pessimistic"],
            "expected": expected[aid], "variance": variance[aid],
            "std": math.sqrt(variance[aid]),
            "predecessors": a["predecessors"],
            "ES": ES[aid], "EF": EF[aid], "LS": LS[aid], "LF": LF[aid],
            "slack": slack[aid], "critical": abs(slack[aid]) < 1e-9,
        })

    # Langkah-langkah
    steps = []
    steps.append({"step": "1. Hitung Expected Duration (Te) untuk setiap aktivitas",
                  "detail": "Rumus PERT: Te = (O + 4M + P) / 6, di mana O=optimis, M=realistis, P=pesimis."})
    for a in activities:
        aid = a["id"]
        steps.append({"step": f"  {aid}: Te = ({a['optimistic']} + 4×{a['most_likely']} + {a['pessimistic']}) / 6 = {expected[aid]:.4f}",
                      "detail": f"Varians = ((P - O) / 6)^2 = (({a['pessimistic']} - {a['optimistic']}) / 6)^2 = {variance[aid]:.4f}"})
    steps.append({"step": "2. Forward Pass - ES & EF (menggunakan Te)",
                  "detail": "Sama seperti CPM, tapi memakai Te sebagai durasi."})
    for aid in topo:
        a = act_dict[aid]
        steps.append({"step": f"  {aid}: ES={ES[aid]:.4f}, EF={EF[aid]:.4f}",
                      "detail": f"EF = ES + Te = {ES[aid]:.4f} + {expected[aid]:.4f} = {EF[aid]:.4f}"})
    steps.append({"step": f"3. Durasi proyek (expected) = {project_duration:.4f}",
                  "detail": "Rata-rata waktu penyelesaian proyek berdasarkan estimasi tiga titik."})
    steps.append({"step": "4. Backward Pass - LS & LF",
                  "detail": "Sama seperti CPM."})
    for aid in reversed(topo):
        steps.append({"step": f"  {aid}: LS={LS[aid]:.4f}, LF={LF[aid]:.4f}",
                      "detail": f"LS = LF - Te = {LF[aid]:.4f} - {expected[aid]:.4f} = {LS[aid]:.4f}"})
    steps.append({"step": "5. Slack dan Jalur Kritis",
                  "detail": f"Slack = LS - ES. Aktivitas dengan slack 0 adalah kritis."})
    steps.append({"step": f"6. Variance proyek = jumlah variance aktivitas kritis = {project_variance:.4f}",
                  "detail": f"Std deviasi proyek = akar(variance) = {project_std:.4f}"})
    steps.append({"step": f"7. Jalur kritis: {' -> '.join(critical_sorted)}",
                  "detail": f"Total variance jalur kritis: {project_variance:.4f}"})

    return {
        "activities": rincian,
        "project_duration": project_duration,
        "project_variance": project_variance,
        "project_std": project_std,
        "critical_path": critical_sorted,
        "steps": steps,
    }


def hitung_probabilitas_pert(result, target):
    """Hitung P(T <= target) menggunakan distribusi normal."""
    mean = result["project_duration"]
    std = result["project_std"]
    if std <= 0:
        return {"z": None, "prob": 1.0 if target >= mean else 0.0, "note": "Std dev = 0"}
    z = (target - mean) / std
    # Aproksimasi CDF normal standar
    prob = 0.5 * (1 + math.erf(z / math.sqrt(2)))
    return {"z": z, "prob": prob}


def interpretasi_pert(result):
    durasi = result["project_duration"]
    std = result["project_std"]
    critical = result["critical_path"]
    teks = (f"Berdasarkan estimasi tiga titik, proyek ini diperkirakan selesai dalam {durasi:.2f} satuan waktu "
            f"(rata-rata). Namun karena ketidakpastian, waktu sebenarnya bisa bervariasi dengan standar deviasi {std:.2f}. "
            f"Jalur kritis: {' -> '.join(critical)}. ")
    if std > 0:
        teks += (f"Dengan asumsi distribusi normal, ada sekitar 84% peluang proyek selesai dalam "
                 f"{durasi + std:.2f} satuan waktu (rata-rata + 1 std dev). "
                 f"Untuk 95% keyakinan, gunakan {durasi + 1.645 * std:.2f} satuan waktu. ")
    teks += ("Semakin besar standar deviasi, semakin tidak pasti perkiraan waktu proyek. "
             "Fokus pengawasan pada aktivitas di jalur kritis.")
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
        lam = float(data.get("lam", 0)); mu = float(data.get("mu", 0))
        if lam <= 0 or mu <= 0: return jsonify({"error": "λ dan μ harus > 0."})
        if model == "mm1": res = mm1(lam, mu)
        elif model == "mmc": res = mmc(lam, mu, int(data.get("c", 2)))
        elif model == "mm1k": res = mm1k(lam, mu, int(data.get("K", 5)))
        elif model == "mg1": res = mg1(lam, mu, float(data.get("sigma", 1 / mu)))
        elif model == "md1": res = md1(lam, mu)
        else: return jsonify({"error": "Model tidak dikenal."})
        if "error" in res: return jsonify(res)
        res["interpretasi"] = interpretasi_antrean(res, lam, mu)
        cw, cs = data.get("c_wait"), data.get("c_server")
        if cw and cs:
            try: res["cost"] = cost_analysis(res, float(cw), float(cs))
            except: pass
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": f"Kesalahan: {str(e)}"})


@app.route("/api/compare", methods=["POST"])
def compare():
    try:
        data = request.get_json()
        lam = float(data["lam"]); mu = float(data["mu"])
        sigma = float(data.get("sigma", 1 / mu))
        rows = []
        for name, fn in [("M/M/1", lambda: mm1(lam, mu)),
                         ("M/D/1", lambda: md1(lam, mu)),
                         ("M/G/1", lambda: mg1(lam, mu, sigma))]:
            r = fn()
            if "error" in r: return jsonify(r)
            rows.append({"model": name, "Lq": round(r["Lq"], 4),
                         "Wq": round(r["Wq"], 4), "W": round(r["W"], 4),
                         "rho": round(r["rho"], 4)})
        return jsonify({"rows": rows})
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/transport", methods=["POST"])
def transport():
    try:
        data = request.get_json()
        cost = data.get("cost"); supply = data.get("supply"); demand = data.get("demand")
        metode = data.get("metode", "nwc")
        if not cost or not supply or not demand:
            return jsonify({"error": "Data harus lengkap."})
        if len(cost) != len(supply):
            return jsonify({"error": "Jumlah baris biaya = jumlah supply."})
        if any(len(row) != len(demand) for row in cost):
            return jsonify({"error": "Panjang tiap baris = jumlah demand."})
        total_s, total_d, balanced = cek_keseimbangan(supply, demand)
        cost2, supply2, demand2, _ = siapkan_matriks(cost, supply, demand)
        if metode == "nwc": alloc, steps = north_west_corner(cost2, supply2, demand2)
        elif metode == "least_cost": alloc, steps = least_cost(cost2, supply2, demand2)
        elif metode == "vam": alloc, steps = vogel_approximation(cost2, supply2, demand2)
        else: return jsonify({"error": "Metode tidak dikenal."})
        total, rincian = hitung_total_biaya(alloc, cost2)
        optimal, _ = hitung_optimum_modi(alloc, cost2)
        interpretasi = interpretasi_transportasi(total, rincian, metode.upper(), balanced, total_s, total_d)
        if not optimal:
            interpretasi += " Solusi ini belum tentu optimal; gunakan MODI untuk perbaikan."
        return jsonify({"metode": metode.upper(), "balanced": balanced,
                        "total_supply": total_s, "total_demand": total_d,
                        "allocation": alloc, "steps": steps, "total_cost": total,
                        "rincian": rincian, "optimal": optimal,
                        "interpretasi": interpretasi,
                        "supply_used": supply2, "demand_used": demand2})
    except Exception as e:
        return jsonify({"error": f"Kesalahan: {str(e)}"})


@app.route("/api/assignment", methods=["POST"])
def assignment():
    try:
        data = request.get_json()
        cost = data.get("cost")
        if not cost or not all(isinstance(row, list) for row in cost):
            return jsonify({"error": "Matriks biaya harus list of list."})
        n = len(cost)
        if n == 0: return jsonify({"error": "Matriks kosong."})
        if any(len(row) != n for row in cost):
            return jsonify({"error": "Matriks harus persegi."})
        res = hungarian(cost)
        if "error" in res: return jsonify(res)
        res["interpretasi"] = interpretasi_penugasan(res["total_cost"], res["assignment"])
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": f"Kesalahan: {str(e)}"})


@app.route("/api/cpm", methods=["POST"])
def cpm():
    try:
        data = request.get_json()
        activities = data.get("activities", [])
        if not activities: return jsonify({"error": "Aktivitas kosong."})
        # Validasi
        for a in activities:
            if not a.get("id"): return jsonify({"error": "Setiap aktivitas harus punya id."})
            if a.get("duration") is None or float(a["duration"]) < 0:
                return jsonify({"error": f"Durasi aktivitas '{a['id']}' harus >= 0."})
        # Konversi tipe
        activities = [{"id": str(a["id"]).strip(),
                       "name": a.get("name", str(a["id"])).strip() or str(a["id"]),
                       "duration": float(a["duration"]),
                       "predecessors": [str(p).strip() for p in a.get("predecessors", []) if str(p).strip()]}
                      for a in activities]
        res = hitung_cpm(activities)
        if "error" in res: return jsonify(res)
        res["interpretasi"] = interpretasi_cpm(res)
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": f"Kesalahan: {str(e)}"})


@app.route("/api/pert", methods=["POST"])
def pert():
    try:
        data = request.get_json()
        activities = data.get("activities", [])
        target = data.get("target")
        if not activities: return jsonify({"error": "Aktivitas kosong."})
        for a in activities:
            if not a.get("id"): return jsonify({"error": "Setiap aktivitas harus punya id."})
            for key in ["optimistic", "most_likely", "pessimistic"]:
                if a.get(key) is None:
                    return jsonify({"error": f"Field '{key}' untuk '{a['id']}' wajib."})
        activities = [{"id": str(a["id"]).strip(),
                       "name": a.get("name", str(a["id"])).strip() or str(a["id"]),
                       "optimistic": float(a["optimistic"]),
                       "most_likely": float(a["most_likely"]),
                       "pessimistic": float(a["pessimistic"]),
                       "predecessors": [str(p).strip() for p in a.get("predecessors", []) if str(p).strip()]}
                      for a in activities]
        res = hitung_pert(activities)
        if "error" in res: return jsonify(res)
        res["interpretasi"] = interpretasi_pert(res)
        # Probabilitas jika target diberikan
        if target is not None and str(target).strip() != "":
            try:
                prob = hitung_probabilitas_pert(res, float(target))
                res["probability"] = prob
                res["target"] = float(target)
            except Exception:
                pass
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": f"Kesalahan: {str(e)}"})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)