"""Relational Root Cause Analysis (RCA) Graph Engine.
Menghubungkan entitas: Channel -> Vendor -> Incident -> ErrorCode -> SOP.
Mendukung Multi-Domain Showcase (Fintech, BPJS Healthcare, B2B SaaS, dan POS Klinik).
"""

import networkx as nx
from typing import Dict, Any, List


class GraphRCAEngine:
    def __init__(self):
        self.G = nx.DiGraph()
        self._build_static_topology()
        self.domain_graphs: Dict[str, nx.DiGraph] = {
            "default": self.G,
            "bpjs": self._build_bpjs_topology(),
            "saas": self._build_saas_topology(),
            "klinik": self._build_klinik_topology(),
        }

    def _build_static_topology(self):
        """Membangun simpul dan relasi dasar topologi perbankan & operasional (Fintech Default)."""
        channels = [
            ("CH_VA_BCA", "VA_BCA", "Channel", "#3B82F6"),
            ("CH_VA_MANDIRI", "VA_MANDIRI", "Channel", "#3B82F6"),
            ("CH_QRIS_GOPAY", "QRIS_GOPAY", "Channel", "#06B6D4"),
            ("CH_CREDIT_CARD", "CREDIT_CARD", "Channel", "#8B5CF6"),
            ("CH_EWALLET_OVO", "EWALLET_OVO", "Channel", "#EC4899"),
        ]
        for node_id, label, n_type, color in channels:
            self.G.add_node(node_id, label=label, type=n_type, color=color, size=32)

        vendors = [
            ("VEN_BCA", "Bank Central Asia (BCA)", "Vendor", "#1E40AF"),
            ("VEN_MANDIRI", "Bank Mandiri", "Vendor", "#1E40AF"),
            ("VEN_ARTAJASA", "Artajasa / Switching Network", "Vendor", "#475569"),
            ("VEN_TELKOM", "Telkom Infra / Submarine FO", "Vendor", "#475569"),
        ]
        for node_id, label, n_type, color in vendors:
            self.G.add_node(node_id, label=label, type=n_type, color=color, size=36)

        errors = [
            ("ERR_TIMEOUT", "ERR_GATEWAY_TIMEOUT", "ErrorCode", "#EF4444"),
            ("ERR_MALFUNCTION", "SYSTEM_MALFUNCTION", "ErrorCode", "#F97316"),
            ("ERR_FUNDS", "INSUFFICIENT_FUNDS", "ErrorCode", "#94A3B8"),
            ("ERR_PIN", "INVALID_PIN", "ErrorCode", "#94A3B8"),
        ]
        for node_id, label, n_type, color in errors:
            self.G.add_node(node_id, label=label, type=n_type, color=color, size=28)

        incidents = [
            ("INC_BCA_SWITCH", "#INC-20260912-BCA: DC Core Switch Migration", "Incident", "#DC2626"),
            ("INC_FO_TELKOM", "#INC-20260804-TELKOM: Submarine Cable Cut", "Incident", "#EA580C"),
            ("INC_KAFKA_LAG", "#INC-20260718-INTERNAL: Kafka Queue Lag", "Incident", "#D97706"),
        ]
        for node_id, label, n_type, color in incidents:
            self.G.add_node(node_id, label=label, type=n_type, color=color, size=40)

        sops = [
            ("SOP_AUTOREFUND", "SOP-01: Auto-Refund & Reversal (30m)", "SOP", "#10B981"),
            ("SOP_L2_ESCALATION", "SOP-02: L2 Bank Contact & Maintenance Banner", "SOP", "#10B981"),
            ("SOP_FAILOVER", "SOP-03: L3 Circuit Breaker & Traffic Failover", "SOP", "#10B981"),
        ]
        for node_id, label, n_type, color in sops:
            self.G.add_node(node_id, label=label, type=n_type, color=color, size=34)

        edges = [
            ("CH_VA_BCA", "VEN_BCA", "ROUTES_VIA"),
            ("CH_VA_MANDIRI", "VEN_MANDIRI", "ROUTES_VIA"),
            ("CH_QRIS_GOPAY", "VEN_ARTAJASA", "ROUTES_VIA"),
            ("CH_CREDIT_CARD", "VEN_TELKOM", "ROUTES_VIA"),
            ("INC_BCA_SWITCH", "VEN_BCA", "AFFECTS"),
            ("INC_BCA_SWITCH", "ERR_TIMEOUT", "TRIGGERS"),
            ("INC_FO_TELKOM", "VEN_TELKOM", "AFFECTS"),
            ("INC_FO_TELKOM", "ERR_TIMEOUT", "TRIGGERS"),
            ("INC_KAFKA_LAG", "CH_QRIS_GOPAY", "AFFECTS"),
            ("INC_KAFKA_LAG", "ERR_MALFUNCTION", "TRIGGERS"),
            ("ERR_TIMEOUT", "SOP_L2_ESCALATION", "GOVERNED_BY"),
            ("ERR_TIMEOUT", "SOP_AUTOREFUND", "GOVERNED_BY"),
            ("ERR_MALFUNCTION", "SOP_FAILOVER", "GOVERNED_BY"),
        ]
        for src, dst, rel in edges:
            self.G.add_edge(src, dst, relation=rel)

    @staticmethod
    def _build_bpjs_topology() -> nx.DiGraph:
        g = nx.DiGraph()
        nodes = [
            ("CH_TIPE_A", "RS Tipe A (Rujukan Nasional)", "Channel", "#3B82F6", 32),
            ("CH_TIPE_B", "RS Tipe B (Rujukan Provinsi)", "Channel", "#3B82F6", 34),
            ("CH_TIPE_C", "RS Tipe C (Pratama)", "Channel", "#06B6D4", 30),
            ("VEN_VCLAIM", "VClaim BPJS & INA-CBG Grouper", "Vendor", "#1E40AF", 36),
            ("VEN_FORNAS", "Komite Formularium Nasional", "Vendor", "#475569", 34),
            ("ERR_RESUME", "Berkas Resume Medis Tidak Lengkap", "ErrorCode", "#EF4444", 30),
            ("ERR_ICD10", "Ketidaksesuaian Koding ICD-10", "ErrorCode", "#F97316", 30),
            ("ERR_LOS", "Plafon Hari Rawat Inap (LOS Exceeded)", "ErrorCode", "#EF4444", 28),
            ("INC_BPJS_AUDIT", "#CLM-AUDIT-Q3: Lonjakan Klaim Pending Tipe B", "Incident", "#DC2626", 40),
            ("SOP_VERIF_BPJS", "SOP-BPJS-01: SLA Verifikasi Klaim 14 Hari Kerja", "SOP", "#10B981", 34),
            ("SOP_KODING_ICD", "SOP-BPJS-02: Audit Koding ICD-10 & Resume Medis", "SOP", "#10B981", 34),
        ]
        for nid, lbl, ntype, col, sz in nodes:
            g.add_node(nid, label=lbl, type=ntype, color=col, size=sz)
        edges = [
            ("CH_TIPE_A", "VEN_VCLAIM", "SUBMITS_TO"),
            ("CH_TIPE_B", "VEN_VCLAIM", "SUBMITS_TO"),
            ("CH_TIPE_C", "VEN_FORNAS", "CHECKED_BY"),
            ("INC_BPJS_AUDIT", "CH_TIPE_B", "AFFECTS"),
            ("INC_BPJS_AUDIT", "ERR_ICD10", "TRIGGERS"),
            ("INC_BPJS_AUDIT", "ERR_RESUME", "TRIGGERS"),
            ("VEN_VCLAIM", "ERR_LOS", "FLAGS"),
            ("ERR_ICD10", "SOP_KODING_ICD", "GOVERNED_BY"),
            ("ERR_RESUME", "SOP_VERIF_BPJS", "GOVERNED_BY"),
            ("ERR_LOS", "SOP_VERIF_BPJS", "GOVERNED_BY"),
        ]
        for s, d, r in edges:
            g.add_edge(s, d, relation=r)
        return g

    @staticmethod
    def _build_saas_topology() -> nx.DiGraph:
        g = nx.DiGraph()
        nodes = [
            ("CH_ENTERPRISE", "Enterprise Tier Tenant", "Channel", "#3B82F6", 34),
            ("CH_GROWTH", "Growth Tier Tenant", "Channel", "#06B6D4", 34),
            ("CH_STARTER", "Starter Tier Tenant", "Channel", "#8B5CF6", 30),
            ("VEN_KONG", "API Gateway & Rate Limiter", "Vendor", "#1E40AF", 36),
            ("VEN_RISK_ENGINE", "Risk Intelligence Cluster", "Vendor", "#475569", 36),
            ("ERR_429", "ERR_RATE_LIMIT_EXCEEDED (HTTP 429)", "ErrorCode", "#F97316", 30),
            ("ERR_504", "ERR_GATEWAY_TIMEOUT (HTTP 504)", "ErrorCode", "#EF4444", 30),
            ("INC_SAAS_SPIKE", "#INC-SAAS-504: /v1/credit-scoring Burst Latency", "Incident", "#DC2626", 40),
            ("SOP_QUOTA", "SOP-SAAS-01: Token Bucket & Burst Quota Isolation", "SOP", "#10B981", 34),
            ("SOP_AUTOSCALE", "SOP-SAAS-02: HPA Pod Autoscale & Circuit Breaker", "SOP", "#10B981", 34),
        ]
        for nid, lbl, ntype, col, sz in nodes:
            g.add_node(nid, label=lbl, type=ntype, color=col, size=sz)
        edges = [
            ("CH_ENTERPRISE", "VEN_KONG", "CALLS"),
            ("CH_GROWTH", "VEN_KONG", "CALLS"),
            ("CH_STARTER", "VEN_KONG", "CALLS"),
            ("VEN_KONG", "VEN_RISK_ENGINE", "UPSTREAM"),
            ("INC_SAAS_SPIKE", "VEN_RISK_ENGINE", "AFFECTS"),
            ("INC_SAAS_SPIKE", "ERR_504", "TRIGGERS"),
            ("CH_GROWTH", "ERR_429", "EXCEEDS_QUOTA"),
            ("ERR_429", "SOP_QUOTA", "GOVERNED_BY"),
            ("ERR_504", "SOP_AUTOSCALE", "GOVERNED_BY"),
        ]
        for s, d, r in edges:
            g.add_edge(s, d, relation=r)
        return g

    @staticmethod
    def _build_klinik_topology() -> nx.DiGraph:
        g = nx.DiGraph()
        nodes = [
            ("CH_TUNAI_CASH", "TUNAI_CASH (Kasir Laci Fisik)", "Channel", "#3B82F6", 34),
            ("VEN_SHIFT_PAGI", "Shift Pagi (Bidan Siti & Rina)", "Vendor", "#1E40AF", 34),
            ("VEN_SHIFT_SORE", "Shift Sore (Bidan Nur & Maya)", "Vendor", "#475569", 34),
            ("ERR_REFUND_KAS", "BATAL_REFUND (Pembatalan Tindakan)", "ErrorCode", "#EF4444", 30),
            ("ERR_PENDING_KAS", "PENDING_VERIFIKASI (Selisih Struk)", "ErrorCode", "#F97316", 30),
            ("INC_SELISIH_LACI", "#AUDIT-WJ-01: Rekonsiliasi Selisih Kas Shift", "Incident", "#DC2626", 38),
            ("SOP_KAS_FISIK", "SOP-WJ-01: Serah Terima Uang Fisik Dua Saksi", "SOP", "#10B981", 34),
            ("SOP_VOID_STRUK", "SOP-WJ-02: Otorisasi Pembatalan Struk Bidan", "SOP", "#10B981", 34),
        ]
        for nid, lbl, ntype, col, sz in nodes:
            g.add_node(nid, label=lbl, type=ntype, color=col, size=sz)
        edges = [
            ("CH_TUNAI_CASH", "VEN_SHIFT_PAGI", "HANDLED_BY"),
            ("CH_TUNAI_CASH", "VEN_SHIFT_SORE", "HANDLED_BY"),
            ("INC_SELISIH_LACI", "CH_TUNAI_CASH", "AFFECTS"),
            ("INC_SELISIH_LACI", "ERR_REFUND_KAS", "TRIGGERS"),
            ("VEN_SHIFT_SORE", "ERR_PENDING_KAS", "REPORTS"),
            ("ERR_REFUND_KAS", "SOP_VOID_STRUK", "GOVERNED_BY"),
            ("ERR_PENDING_KAS", "SOP_KAS_FISIK", "GOVERNED_BY"),
        ]
        for s, d, r in edges:
            g.add_edge(s, d, relation=r)
        return g

    def get_cytoscape_elements(
        self,
        highlight_channel: str = None,
        dynamic_subgraph_only: bool = False,
        domain: str = "default",
    ) -> List[Dict[str, Any]]:
        """Mengonversi NetworkX Graph ke format Cytoscape.js dengan highlight anomali atau proyeksi subgraph dinamis."""
        graph = self.domain_graphs.get((domain or "default").lower(), self.G)
        elements = []

        highlighted_nodes = set()
        if highlight_channel:
            ch_key = highlight_channel.upper().replace(" ", "_")
            for n, ndata in graph.nodes(data=True):
                n_label = str(ndata.get("label", "")).upper().replace(" ", "_")
                if ch_key in n or ch_key in n_label or any(
                    p in n or p in n_label for p in ch_key.split("_") if len(p) > 2
                ):
                    highlighted_nodes.add(n)
                    for neighbor in graph.neighbors(n):
                        highlighted_nodes.add(neighbor)
                    for pred in graph.predecessors(n):
                        highlighted_nodes.add(pred)

            if graph is self.G:
                if "BCA" in ch_key:
                    highlighted_nodes.update(["INC_BCA_SWITCH", "VEN_BCA", "ERR_TIMEOUT", "SOP_L2_ESCALATION", "SOP_AUTOREFUND", "CH_VA_BCA"])
                elif "MANDIRI" in ch_key:
                    highlighted_nodes.update(["VEN_MANDIRI", "CH_VA_MANDIRI"])
                elif "TELKOM" in ch_key or "CARD" in ch_key:
                    highlighted_nodes.update(["INC_FO_TELKOM", "VEN_TELKOM", "ERR_TIMEOUT", "CH_CREDIT_CARD", "SOP_L2_ESCALATION"])
                elif "QRIS" in ch_key or "GOPAY" in ch_key:
                    highlighted_nodes.update(["INC_KAFKA_LAG", "CH_QRIS_GOPAY", "VEN_ARTAJASA", "ERR_MALFUNCTION", "SOP_FAILOVER"])

        target_nodes = list(graph.nodes(data=True))
        if dynamic_subgraph_only and highlighted_nodes:
            target_nodes = [(n, d) for n, d in target_nodes if n in highlighted_nodes]

        valid_node_ids = {n for n, _ in target_nodes}

        for node_id, data in target_nodes:
            is_active = (node_id in highlighted_nodes) if highlight_channel else False
            elements.append({
                "data": {
                    "id": node_id,
                    "label": data.get("label", node_id),
                    "type": data.get("type", "Generic"),
                    "color": "#FF2A55" if is_active and data.get("type") in ["Channel", "Incident"] else data.get("color", "#64748B"),
                    "size": (data.get("size", 30) + 12) if is_active else data.get("size", 30),
                    "is_active": is_active,
                    "highlighted": is_active
                }
            })

        for src, dst, data in graph.edges(data=True):
            if src not in valid_node_ids or dst not in valid_node_ids:
                continue
            is_active_edge = (src in highlighted_nodes and dst in highlighted_nodes) if highlight_channel else False
            elements.append({
                "data": {
                    "id": f"{src}_{dst}",
                    "source": src,
                    "target": dst,
                    "label": data.get("relation", ""),
                    "color": "#FF2A55" if is_active_edge else "rgba(148, 163, 184, 0.25)",
                    "width": 3 if is_active_edge else 1
                }
            })

        return elements
