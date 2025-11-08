import threading
import time
import json
from pathlib import Path
import customtkinter as ctk
import requests
from tkinter import filedialog, messagebox
import tkinter.ttk as ttk
from typing import List

from core.proxy.scraper import scrape_from_sources
from core.proxy.validator import validate_proxy


class ProxyManagerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Proxy Manager & Validator")
        self.geometry("1100x700")
        ctk.set_default_color_theme("dark-blue")

        # State
        self._scraping_thread = None
        self._validation_thread = None
        self._stop_flag = False
        self._proxies: List[dict] = []
        self._valid_count = 0
        self._status_text = ctk.StringVar(value="Idle")
        self._scheduler_autorefresh = False
        self._scheduler_after_id = None

        # Layout
        self._build_layout()
        # Carregar configurações da UI
        try:
            self._load_ui_settings()
        except Exception:
            pass

    def _build_layout(self):
        # Top config panel
        config_frame = ctk.CTkFrame(self)
        config_frame.pack(fill="x", padx=10, pady=10)

        self.country_entry = ctk.CTkEntry(config_frame, placeholder_text="Country (ISO) opcional")
        self.country_entry.pack(side="left", padx=5)

        self.quantity_spin = ctk.CTkEntry(config_frame)
        self.quantity_spin.insert(0, "100")
        self.quantity_spin.pack(side="left", padx=5)

        self.protocol_http = ctk.CTkCheckBox(config_frame, text="HTTP")
        self.protocol_http.select()
        self.protocol_http.pack(side="left", padx=5)
        self.protocol_https = ctk.CTkCheckBox(config_frame, text="HTTPS")
        self.protocol_https.select()
        self.protocol_https.pack(side="left", padx=5)

        self.scrape_button = ctk.CTkButton(config_frame, text="Start Scraping", command=self._start_scraping)
        self.scrape_button.pack(side="left", padx=10)
        self.stop_button = ctk.CTkButton(config_frame, text="Stop", command=self._stop_operations)
        self.stop_button.pack(side="left", padx=5)

        self.import_button = ctk.CTkButton(config_frame, text="Import from File", command=self._import_file)
        self.import_button.pack(side="left", padx=10)

        # Results panel
        results_frame = ctk.CTkFrame(self)
        results_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.table = ctk.CTkTextbox(results_frame)
        self.table.pack(fill="both", expand=True)

        # Validation panel
        validation_frame = ctk.CTkFrame(self)
        validation_frame.pack(fill="x", padx=10, pady=10)

        self.timeout_entry = ctk.CTkEntry(validation_frame)
        self.timeout_entry.insert(0, "10")
        self.timeout_entry.pack(side="left", padx=5)

        self.urls_entry = ctk.CTkEntry(validation_frame, placeholder_text="URLs de teste separadas por vírgula")
        self.urls_entry.insert(0, "https://lovable.dev,https://mail.tm")
        self.urls_entry.pack(side="left", padx=5, fill="x", expand=True)

        self.test_all_check = ctk.CTkCheckBox(validation_frame, text="Testar todas URLs")
        self.test_all_check.select()
        self.test_all_check.pack(side="left", padx=5)

        self.validate_button = ctk.CTkButton(validation_frame, text="Start Validation", command=self._start_validation)
        self.validate_button.pack(side="left", padx=10)

        # Status bar
        status_frame = ctk.CTkFrame(self)
        status_frame.pack(fill="x", padx=10, pady=5)
        self.status_label = ctk.CTkLabel(status_frame, textvariable=self._status_text)
        self.status_label.pack(side="left")

        # Scheduler panel (API)
        scheduler_frame = ctk.CTkFrame(self)
        scheduler_frame.pack(fill="both", expand=False, padx=10, pady=10)

        self.base_url_entry = ctk.CTkEntry(scheduler_frame, placeholder_text="Base URL da API")
        self.base_url_entry.insert(0, "http://localhost:8000")
        self.base_url_entry.pack(side="left", padx=5)

        self.api_key_entry = ctk.CTkEntry(scheduler_frame, placeholder_text="X-API-Key (opcional)")
        self.api_key_entry.pack(side="left", padx=5)

        self.bearer_entry = ctk.CTkEntry(scheduler_frame, placeholder_text="Bearer Token (opcional)")
        self.bearer_entry.pack(side="left", padx=5)

        self.scheduler_refresh_btn = ctk.CTkButton(scheduler_frame, text="Atualizar Status do Scheduler", command=self._update_scheduler_status)
        self.scheduler_refresh_btn.pack(side="left", padx=10)

        self.scheduler_enable_btn = ctk.CTkButton(scheduler_frame, text="Ligar Scheduler", command=lambda: self._scheduler_set_enabled(True))
        self.scheduler_enable_btn.pack(side="left", padx=5)

        self.scheduler_disable_btn = ctk.CTkButton(scheduler_frame, text="Desligar Scheduler", command=lambda: self._scheduler_set_enabled(False))
        self.scheduler_disable_btn.pack(side="left", padx=5)

        self.scheduler_auto_refresh_check = ctk.CTkCheckBox(scheduler_frame, text="Auto-refresh", command=self._toggle_scheduler_autorefresh)
        self.scheduler_auto_refresh_check.pack(side="left", padx=10)

        self.scheduler_auto_refresh_interval = ctk.CTkEntry(scheduler_frame, placeholder_text="Intervalo ms")
        self.scheduler_auto_refresh_interval.insert(0, "5000")
        self.scheduler_auto_refresh_interval.pack(side="left", padx=5)

        self.scheduler_text = ctk.CTkTextbox(self)
        self.scheduler_text.pack(fill="both", expand=False, padx=10, pady=5, ipady=5)

        # Linha de ação: Scrape Agora
        action_frame = ctk.CTkFrame(self)
        action_frame.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(action_frame, text="Quantidade para Scrape:").pack(side="left", padx=(10, 4))
        self.scheduler_scrape_qty_entry = ctk.CTkEntry(action_frame, width=80)
        self.scheduler_scrape_qty_entry.insert(0, "100")
        self.scheduler_scrape_qty_entry.pack(side="left")
        self.scheduler_scrape_now_btn = ctk.CTkButton(action_frame, text="Scrape Agora", command=self._run_scrape_now)
        self.scheduler_scrape_now_btn.pack(side="left", padx=10)

        # Seção: Validar Agora
        validate_frame = ctk.CTkFrame(self)
        validate_frame.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(validate_frame, text="Proxies para Validar (um por linha):").pack(anchor="w", padx=10)
        self.scheduler_validate_proxies_text = ctk.CTkTextbox(validate_frame, height=120)
        self.scheduler_validate_proxies_text.pack(fill="x", padx=10, pady=(4, 8))
        urls_row = ctk.CTkFrame(validate_frame)
        urls_row.pack(fill="x", padx=10, pady=(0, 6))
        ctk.CTkLabel(urls_row, text="Test URLs (separadas por vírgula):").pack(side="left")
        self.scheduler_validate_urls_entry = ctk.CTkEntry(urls_row)
        self.scheduler_validate_urls_entry.insert(0, "http://example.com")
        self.scheduler_validate_urls_entry.pack(side="left", padx=6, fill="x", expand=True)
        self.scheduler_validate_now_btn = ctk.CTkButton(validate_frame, text="Validar Agora", command=self._run_validate_now)
        self.scheduler_validate_now_btn.pack(anchor="w", padx=10, pady=(4, 0))

        # Proxies (API) — Tabela com filtros
        api_frame = ctk.CTkFrame(self)
        api_frame.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(api_frame, text="Lista de Proxies (API)").pack(side="left", padx=5)
        self.api_filter_country = ctk.CTkEntry(api_frame, width=120, placeholder_text="País (ISO)")
        self.api_filter_country.pack(side="left", padx=5)
        self.api_filter_protocol = ctk.CTkOptionMenu(api_frame, values=["any","http","https","socks4","socks5"])
        self.api_filter_protocol.set("any")
        self.api_filter_protocol.pack(side="left", padx=5)
        self.api_filter_valid = ctk.CTkCheckBox(api_frame, text="Somente válidos")
        self.api_filter_valid.pack(side="left", padx=5)
        self.api_filter_maxlat = ctk.CTkEntry(api_frame, width=120, placeholder_text="Latência máx (ms)")
        self.api_filter_maxlat.pack(side="left", padx=5)
        self.api_filter_orderby = ctk.CTkOptionMenu(api_frame, values=["avg_response_time_ms","last_checked"])
        self.api_filter_orderby.set("last_checked")
        self.api_filter_orderby.pack(side="left", padx=5)
        self.api_filter_order = ctk.CTkOptionMenu(api_frame, values=["desc","asc"])
        self.api_filter_order.set("desc")
        self.api_filter_order.pack(side="left", padx=5)
        self.api_refresh_btn = ctk.CTkButton(api_frame, text="Atualizar", command=self._refresh_api_table)
        self.api_refresh_btn.pack(side="left", padx=10)

        table_frame = ctk.CTkFrame(self)
        table_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.api_tree = ttk.Treeview(table_frame, columns=("ip","port","protocol","country","anonymity","avg_ms","valid","last_checked"), show="headings", height=9)
        for col, text, width in (
            ("ip","IP",140),
            ("port","Porta",70),
            ("protocol","Protocolo",95),
            ("country","País",80),
            ("anonymity","Anonimato",110),
            ("avg_ms","Latência (ms)",120),
            ("valid","Válido",70),
            ("last_checked","Última checagem",180),
        ):
            self.api_tree.heading(col, text=text)
            self.api_tree.column(col, width=width, anchor="center")
        self.api_tree.pack(fill="both", expand=True)
        # buffer local de items
        self._api_rows = []

        # Barra de ações em lote
        actions_frame = ctk.CTkFrame(self)
        actions_frame.pack(fill="x", padx=10, pady=(0, 10))
        self.api_validate_sel_btn = ctk.CTkButton(actions_frame, text="Validar Selecionados", command=self._api_validate_selected)
        self.api_validate_sel_btn.pack(side="left", padx=5)
        self.api_delete_invalid_btn = ctk.CTkButton(actions_frame, text="Excluir Inválidos", command=self._api_delete_invalids)
        self.api_delete_invalid_btn.pack(side="left", padx=5)
        self.api_export_json_btn = ctk.CTkButton(actions_frame, text="Exportar JSON", command=lambda: self._api_export(format="json"))
        self.api_export_json_btn.pack(side="left", padx=5)
        self.api_export_csv_btn = ctk.CTkButton(actions_frame, text="Exportar CSV", command=lambda: self._api_export(format="csv"))
        self.api_export_csv_btn.pack(side="left", padx=5)
        self.api_copy_sel_btn = ctk.CTkButton(actions_frame, text="Copiar Selecionados", command=self._api_copy_selected)
        self.api_copy_sel_btn.pack(side="left", padx=5)

    def _get_protocols(self) -> List[str]:
        protos = []
        if self.protocol_http.get():
            protos.append("http")
        if self.protocol_https.get():
            protos.append("https")
        return protos

    def _append_table(self, line: str):
        self.table.insert("end", line + "\n")
        self.table.see("end")

    def _api_base_url(self) -> str:
        base = (self.base_url_entry.get() or "http://localhost:8000").strip().rstrip("/")
        return base

    def _refresh_api_table(self):
        def worker():
            base = self._api_base_url()
            url = f"{base}/api/v1/proxies"
            params = {}
            country = (self.api_filter_country.get() or "").strip()
            if country:
                params["country"] = country
            proto = (self.api_filter_protocol.get() or "any").strip()
            if proto and proto != "any":
                params["protocol"] = proto
            if bool(self.api_filter_valid.get()):
                params["valid_only"] = True
            maxlat = (self.api_filter_maxlat.get() or "").strip()
            order_by = (self.api_filter_orderby.get() or "last_checked").strip()
            order = (self.api_filter_order.get() or "desc").strip()
            if order_by:
                params["order_by"] = order_by
            if order:
                params["order"] = order

            self._status_text.set("Carregando proxies da API...")
            try:
                headers = self._build_auth_headers()
                r = requests.get(url, params=params, headers=headers, timeout=10)
                if r.status_code == 429:
                    retry_after = r.headers.get("Retry-After") or r.headers.get("X-RateLimit-Reset")
                    self._status_text.set("Rate limit excedido na listagem")
                    messagebox.showwarning("Rate limit", f"429 Too Many Requests. Tente novamente em: {retry_after} s")
                    return
                if r.status_code != 200:
                    self._status_text.set(f"Falha ao listar: {r.status_code}")
                    messagebox.showerror("Erro", f"Erro ao listar proxies: HTTP {r.status_code}\n{r.text[:300]}")
                    return
                data = r.json()
            except Exception as e:
                self._status_text.set("Erro na listagem da API")
                messagebox.showerror("Erro", f"Exceção na listagem: {e}")
                return

            try:
                items = data.get("proxies") or []
                # filtro local por latência máxima, se fornecido
                if maxlat.isdigit():
                    try:
                        maxlat_int = int(maxlat)
                        items = [it for it in items if (it.get("avg_response_time_ms") is None) or (int(it.get("avg_response_time_ms")) <= maxlat_int)]
                    except Exception:
                        pass
                self._api_rows = items
                for i in self.api_tree.get_children():
                    self.api_tree.delete(i)
                for item in items:
                    self.api_tree.insert("", "end", values=(
                        item.get("ip"),
                        item.get("port"),
                        (item.get("protocol") or "").upper(),
                        item.get("country") or "",
                        item.get("anonymity") or "",
                        (int(item.get("avg_response_time_ms")) if item.get("avg_response_time_ms") is not None else "-"),
                        "✓" if item.get("valid") else "✗",
                        item.get("last_checked") or "",
                    ))
                total = int(data.get("total") or len(items))
                self._status_text.set(f"Listagem concluída: {total} proxies carregados")
            except Exception:
                self._status_text.set("Erro ao preencher tabela")

        threading.Thread(target=worker, daemon=True).start()

    def _api_selected_proxies(self) -> List[str]:
        items = []
        try:
            for iid in self.api_tree.selection():
                vals = self.api_tree.item(iid, "values")
                ip, port, proto = vals[0], vals[1], (vals[2] or "").lower()
                if proto:
                    items.append(f"{proto}://{ip}:{port}")
                else:
                    items.append(f"{ip}:{port}")
        except Exception:
            pass
        return items

    def _api_validate_selected(self):
        def worker():
            base = self._api_base_url()
            url = f"{base}/api/v1/proxies/validate"
            headers = self._build_auth_headers()
            proxies = self._api_selected_proxies()
            if not proxies:
                messagebox.showinfo("Validação", "Nenhum item selecionado na tabela.")
                return
            urls_raw = (self.scheduler_validate_urls_entry.get() or "http://example.com").strip()
            test_urls = [u.strip() for u in urls_raw.split(",") if u.strip()] or ["http://example.com"]
            payload = {
                "proxies": proxies,
                "test_urls": test_urls,
                "timeout": 10,
                "check_anonymity": False,
                "check_geolocation": False,
                "concurrent_tests": 20,
                "test_all_urls": True,
            }
            self._status_text.set("Validando selecionados...")
            try:
                r = requests.post(url, json=payload, headers=headers, timeout=30)
                if r.status_code == 429:
                    retry_after = r.headers.get("Retry-After") or r.headers.get("X-RateLimit-Reset")
                    self._status_text.set("Rate limit excedido na validação")
                    messagebox.showwarning("Rate limit", f"429 Too Many Requests. Tente novamente em: {retry_after} s")
                    return
                if r.status_code != 200:
                    self._status_text.set(f"Falha: {r.status_code}")
                    messagebox.showerror("Erro", f"Erro ao validar: HTTP {r.status_code}\n{r.text[:300]}")
                    return
                data = r.json()
            except Exception as e:
                self._status_text.set("Erro na validação")
                messagebox.showerror("Erro", f"Exceção na validação: {e}")
                return
            # Resumo
            try:
                valid = int(data.get("valid_proxies") or 0)
                total = int(data.get("total_tested") or 0)
                rate = (valid / total) if total else 0.0
                bar_len = 30
                filled = int(round(rate * bar_len))
                bar = "#" * filled + "-" * (bar_len - filled)
                self.scheduler_text.delete("1.0", "end")
                self.scheduler_text.insert("end", f"Validar Selecionados — Válidos: {valid}/{total}\n[{bar}] {round(rate*100,1)}%\n")
            except Exception:
                pass
            self._status_text.set("Validação concluída (selecionados)")
        threading.Thread(target=worker, daemon=True).start()

    def _api_delete_invalids(self):
        def worker():
            base = self._api_base_url()
            url = f"{base}/api/v1/proxies"
            headers = self._build_auth_headers()
            self._status_text.set("Excluindo inválidos...")
            try:
                r = requests.delete(url, params={"invalid_only": True}, headers=headers, timeout=12)
                if r.status_code == 429:
                    retry_after = r.headers.get("Retry-After") or r.headers.get("X-RateLimit-Reset")
                    self._status_text.set("Rate limit excedido na deleção")
                    messagebox.showwarning("Rate limit", f"429 Too Many Requests. Tente novamente em: {retry_after} s")
                    return
                if r.status_code != 200:
                    self._status_text.set(f"Falha: {r.status_code}")
                    messagebox.showerror("Erro", f"Erro ao excluir inválidos: HTTP {r.status_code}\n{r.text[:300]}")
                    return
                data = r.json()
            except Exception as e:
                self._status_text.set("Erro na deleção")
                messagebox.showerror("Erro", f"Exceção ao excluir: {e}")
                return
            try:
                removed = int(data.get("removed") or 0)
                self._status_text.set(f"Inválidos removidos: {removed}")
                self._refresh_api_table()
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()

    def _api_export(self, format: str = "json"):
        def worker():
            base = self._api_base_url()
            url = f"{base}/api/v1/proxies/export"
            headers = self._build_auth_headers()
            # Reutilizar filtros atuais
            params = {}
            country = (self.api_filter_country.get() or "").strip()
            if country:
                params["country"] = country
            proto = (self.api_filter_protocol.get() or "any").strip()
            if proto and proto != "any":
                params["protocol"] = proto
            if bool(self.api_filter_valid.get()):
                params["valid_only"] = True
            order_by = (self.api_filter_orderby.get() or "last_checked").strip()
            order = (self.api_filter_order.get() or "desc").strip()
            if order_by:
                params["order_by"] = order_by
            if order:
                params["order"] = order
            params["format"] = format

            self._status_text.set(f"Exportando ({format})...")
            try:
                r = requests.get(url, params=params, headers=headers, timeout=20)
                if r.status_code == 429:
                    retry_after = r.headers.get("Retry-After") or r.headers.get("X-RateLimit-Reset")
                    self._status_text.set("Rate limit excedido na exportação")
                    messagebox.showwarning("Rate limit", f"429 Too Many Requests. Tente novamente em: {retry_after} s")
                    return
                if r.status_code != 200:
                    self._status_text.set(f"Falha: {r.status_code}")
                    messagebox.showerror("Erro", f"Erro ao exportar: HTTP {r.status_code}\n{r.text[:300]}")
                    return
                content = r.text
            except Exception as e:
                self._status_text.set("Erro na exportação")
                messagebox.showerror("Erro", f"Exceção ao exportar: {e}")
                return

            try:
                default_ext = ".json" if format == "json" else ".txt"
                path = filedialog.asksaveasfilename(title="Salvar export", defaultextension=default_ext, filetypes=[
                    ("JSON", ".json"), ("Texto", ".txt"), ("Todos", ".*")
                ])
                if not path:
                    self._status_text.set("Exportação cancelada")
                    return
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content)
                self._status_text.set(f"Exportação salva em: {path}")
            except Exception as e:
                self._status_text.set("Erro ao salvar export")
                messagebox.showerror("Erro", f"Falha ao salvar arquivo: {e}")
        threading.Thread(target=worker, daemon=True).start()

    def _api_copy_selected(self):
        try:
            lines = self._api_selected_proxies()
            if not lines:
                messagebox.showinfo("Copiar", "Nenhum item selecionado na tabela.")
                return
            self.clipboard_clear()
            self.clipboard_append("\n".join(lines))
            self._status_text.set(f"Copiados {len(lines)} proxies para o clipboard")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao copiar: {e}")

    def _start_scraping(self):
        if self._scraping_thread and self._scraping_thread.is_alive():
            return
        self._stop_flag = False
        country = self.country_entry.get().strip() or None
        try:
            quantity = int(self.quantity_spin.get().strip())
        except Exception:
            quantity = 100
        protocols = self._get_protocols()

        def worker():
            self._status_text.set("Scraping...")
            start = time.time()
            try:
                proxies = ctk.CTk._context_manager.run_coroutine(scrape_from_sources(country, protocols, [], quantity))
            except Exception:
                proxies = []
            self._proxies = proxies
            self.table.delete("1.0", "end")
            for p in proxies:
                self._append_table(f"{p.get('ip')}:{p.get('port')} {p.get('protocol').upper()} {p.get('country') or ''}")
            elapsed = int((time.time() - start) * 1000)
            self._status_text.set(f"Scraping concluído: {len(proxies)} proxies em {elapsed} ms")

        self._scraping_thread = threading.Thread(target=worker, daemon=True)
        self._scraping_thread.start()

    def _stop_operations(self):
        self._stop_flag = True
        self._status_text.set("Operação cancelada")

    def _import_file(self):
        path = filedialog.askopenfilename(title="Selecione arquivo .txt", filetypes=[("Text", "*.txt"), ("All", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f.readlines() if l.strip()]
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao ler arquivo: {e}")
            return
        # Parse simples ip:port
        proxies = []
        for l in lines:
            try:
                if "://" in l:
                    proto, host = l.split("://", 1)
                else:
                    proto, host = "http", l
                ip, port = host.split(":", 1)
                proxies.append({"ip": ip, "port": int(port), "protocol": proto})
            except Exception:
                continue
        self._proxies = proxies
        self.table.delete("1.0", "end")
        for p in proxies:
            self._append_table(f"{p.get('ip')}:{p.get('port')} {p.get('protocol').upper()}")
        self._status_text.set(f"Importados {len(proxies)} proxies")

    def _start_validation(self):
        if self._validation_thread and self._validation_thread.is_alive():
            return
        self._stop_flag = False
        urls = [u.strip() for u in self.urls_entry.get().split(",") if u.strip()]
        try:
            timeout = int(self.timeout_entry.get().strip())
        except Exception:
            timeout = 10
        test_all = bool(self.test_all_check.get())

        def worker():
            self._status_text.set("Validando...")
            self._valid_count = 0
            for p in list(self._proxies):
                if self._stop_flag:
                    break
                try:
                    res = ctk.CTk._context_manager.run_coroutine(validate_proxy(p, urls, timeout=timeout, test_all_urls=test_all))
                except Exception:
                    res = {"valid": False}
                mark = "✓" if res.get("valid") else "✗"
                self._append_table(f"[{mark}] {p.get('ip')}:{p.get('port')} {p.get('protocol').upper()} avg={res.get('avg_response_time_ms') or '-'}ms")
                if res.get("valid"):
                    self._valid_count += 1
            self._status_text.set(f"Validação concluída. Válidos: {self._valid_count}")

        self._validation_thread = threading.Thread(target=worker, daemon=True)
        self._validation_thread.start()

    def _build_auth_headers(self) -> dict:
        headers = {"Accept": "application/json"}
        api_key = (self.api_key_entry.get() or "").strip()
        bearer = (self.bearer_entry.get() or "").strip()
        if api_key:
            headers["x-api-key"] = api_key
        if bearer:
            if not bearer.lower().startswith("bearer "):
                headers["Authorization"] = f"Bearer {bearer}"
            else:
                headers["Authorization"] = bearer
        return headers

    def _update_scheduler_status(self):
        def worker():
            base = (self.base_url_entry.get() or "http://localhost:8000").strip()
            base = base.rstrip("/")
            url = f"{base}/api/v1/proxies/scheduler/status"
            self._status_text.set("Consultando scheduler...")
            try:
                headers = self._build_auth_headers()
                r = requests.get(url, headers=headers, timeout=8)
                if r.status_code == 429:
                    retry_after = r.headers.get("Retry-After") or r.headers.get("X-RateLimit-Reset")
                    self._status_text.set("Rate limit excedido")
                    self.scheduler_text.delete("1.0", "end")
                    self.scheduler_text.insert("end", f"429 Too Many Requests. Tente novamente em: {retry_after} s\n")
                    return
                if r.status_code != 200:
                    self._status_text.set(f"Falha: {r.status_code}")
                    self.scheduler_text.delete("1.0", "end")
                    self.scheduler_text.insert("end", f"Erro ao consultar: HTTP {r.status_code}\n{r.text[:500]}")
                    return
                data = r.json()
            except Exception as e:
                self._status_text.set("Erro na consulta do scheduler")
                self.scheduler_text.delete("1.0", "end")
                self.scheduler_text.insert("end", f"Exceção: {e}")
                return

            # Renderizar status resumido e métricas
            lines = []
            lines.append("=== Scheduler Status ===")
            lines.append(f"enabled: {data.get('enabled')}")
            lines.append(f"running: {data.get('running')}")
            lines.append(f"validate_interval_min: {data.get('validate_interval_min')}")
            lines.append(f"scrape_interval_min: {data.get('scrape_interval_min')}")
            lines.append(f"validate_batch_size: {data.get('validate_batch_size')}")
            lines.append(f"scrape_quantity: {data.get('scrape_quantity')}")
            lines.append(f"last_validate_at: {data.get('last_validate_at')}")
            lines.append(f"last_scrape_at: {data.get('last_scrape_at')}")
            lines.append("")

            vm = data.get("last_validate_metrics") or {}
            if vm:
                lines.append("-- Última Validação --")
                lines.append(f"job_id: {vm.get('job_id')}")
                lines.append(f"duration_seconds: {vm.get('duration_seconds')}")
                lines.append(f"total_tested: {vm.get('total_tested')}")
                lines.append(f"valid: {vm.get('valid')} | invalid: {vm.get('invalid')}")
                lines.append(f"success_rate: {vm.get('success_rate')}")
                art = vm.get('avg_response_time_ms_valid')
                lines.append(f"avg_response_time_ms_valid: {art if art is not None else '-'}")
                # Progresso do job de validação (se em execução)
                if data.get("running") and vm.get("job_id"):
                    jurl = f"{base}/jobs/{vm.get('job_id')}"
                    try:
                        jr = requests.get(jurl, headers=headers, timeout=6)
                        if jr.status_code == 200:
                            jd = jr.json()
                            lines.append("")
                            lines.append("[Job de Validação]")
                            lines.append(f"status: {jd.get('status')}")
                            prog = jd.get('progress')
                            lines.append(f"progress: {round(prog*100, 1)}%" if isinstance(prog, (int, float)) else f"progress: {prog}")
                            lines.append(f"eta_seconds: {jd.get('eta_seconds')}")
                            lines.append(f"duration_seconds: {jd.get('duration_seconds')}")
                    except Exception:
                        pass
                lines.append("")

            sm = data.get("last_scrape_metrics") or {}
            if sm:
                lines.append("-- Último Scrape --")
                lines.append(f"job_id: {sm.get('job_id')}")
                lines.append(f"duration_seconds: {sm.get('duration_seconds')}")
                lines.append(f"total_found: {sm.get('total_found')}")
                lines.append(f"saved: {sm.get('saved')}")
                bys = sm.get("by_source") or {}
                if bys:
                    lines.append("by_source:")
                    for k, v in bys.items():
                        lines.append(f"  - {k}: {v}")
                # Progresso do job de scraping (se em execução)
                if data.get("running") and sm.get("job_id"):
                    jurl2 = f"{base}/jobs/{sm.get('job_id')}"
                    try:
                        jr2 = requests.get(jurl2, headers=headers, timeout=6)
                        if jr2.status_code == 200:
                            jd2 = jr2.json()
                            lines.append("")
                            lines.append("[Job de Scraping]")
                            lines.append(f"status: {jd2.get('status')}")
                            prog2 = jd2.get('progress')
                            lines.append(f"progress: {round(prog2*100, 1)}%" if isinstance(prog2, (int, float)) else f"progress: {prog2}")
                            lines.append(f"eta_seconds: {jd2.get('eta_seconds')}")
                            lines.append(f"duration_seconds: {jd2.get('duration_seconds')}")
                    except Exception:
                        pass

            # Gráficos ASCII simples
            try:
                # Barra de sucesso da validação
                rate = (vm.get('success_rate') if vm else None)
                if isinstance(rate, (float, int)) and 0 <= rate <= 1:
                    bar_len = 20
                    filled = int(round(rate * bar_len))
                    bar = "#" * filled + "-" * (bar_len - filled)
                    lines.append(f"success_rate_chart: [{bar}] {round(rate*100,1)}%")
                # Barras por fonte no scrape
                bys = (sm.get('by_source') if sm else None) or {}
                if bys:
                    lines.append("by_source_chart:")
                    # Top 5 fontes
                    items = sorted(bys.items(), key=lambda kv: kv[1], reverse=True)[:5]
                    maxv = max(v for _, v in items) if items else 0
                    bar_len2 = 20
                    for k, v in items:
                        filled2 = int(round((v / maxv) * bar_len2)) if maxv > 0 else 0
                        bar2 = "#" * filled2 + "-" * (bar_len2 - filled2)
                        lines.append(f"  {k}: {v} [{bar2}]")
            except Exception:
                pass

            self.scheduler_text.delete("1.0", "end")
            self.scheduler_text.insert("end", "\n".join(lines))
            self._status_text.set("Scheduler status atualizado")
            # Persistir configurações após consulta bem-sucedida
            try:
                self._save_ui_settings()
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _run_scrape_now(self):
        def worker():
            base = (self.base_url_entry.get() or "http://localhost:8000").strip().rstrip("/")
            url = f"{base}/api/v1/proxies/schedule"
            headers = self._build_auth_headers()
            try:
                quantity_str = (self.scheduler_scrape_qty_entry.get() or "100").strip()
                quantity = int(quantity_str) if quantity_str.isdigit() else 100
            except Exception:
                quantity = 100
            payload = {"type": "scrape", "quantity": quantity}
            self._status_text.set("Agendando scrape agora...")
            try:
                r = requests.post(url, json=payload, headers=headers, timeout=10)
                if r.status_code == 429:
                    retry_after = r.headers.get("Retry-After") or r.headers.get("X-RateLimit-Reset")
                    self._status_text.set("Rate limit excedido ao agendar")
                    self.scheduler_text.delete("1.0", "end")
                    self.scheduler_text.insert("end", f"429 Too Many Requests. Tente novamente em: {retry_after} s\n")
                    return
                if r.status_code != 200:
                    self._status_text.set(f"Falha ao agendar: {r.status_code}")
                    self.scheduler_text.delete("1.0", "end")
                    self.scheduler_text.insert("end", f"Erro ao agendar scrape: HTTP {r.status_code}\n{r.text[:500]}")
                    return
                data = r.json()
                job_id = data.get("job_id")
                polling_url = data.get("polling_url")
                self.scheduler_text.delete("1.0", "end")
                self.scheduler_text.insert("end", f"Scrape agendado. job_id={job_id} polling={polling_url}\n")
                self._status_text.set("Scrape agendado com sucesso")
                # Consultar progresso imediato
                if polling_url:
                    jurl = f"{base}{polling_url}"
                    try:
                        jr = requests.get(jurl, headers=headers, timeout=6)
                        if jr.status_code == 200:
                            jd = jr.json()
                            self.scheduler_text.insert("end", f"status: {jd.get('status')} progress={jd.get('progress')}\n")
                    except Exception:
                        pass
                # Atualiza status do scheduler para refletir última métrica
                try:
                    self._update_scheduler_status()
                except Exception:
                    pass
                try:
                    self._save_ui_settings()
                except Exception:
                    pass
            except Exception as e:
                self._status_text.set("Erro ao agendar scrape")
                self.scheduler_text.delete("1.0", "end")
                self.scheduler_text.insert("end", f"Exceção: {e}")
                return
        threading.Thread(target=worker, daemon=True).start()

    def _run_validate_now(self):
        def worker():
            base = (self.base_url_entry.get() or "http://localhost:8000").strip().rstrip("/")
            url = f"{base}/api/v1/proxies/validate"
            headers = self._build_auth_headers()
            # Coletar proxies
            raw = (self.scheduler_validate_proxies_text.get("1.0", "end") or "").strip()
            proxies = [line.strip() for line in raw.splitlines() if line.strip()]
            # Coletar URLs de teste
            urls_raw = (self.scheduler_validate_urls_entry.get() or "http://example.com").strip()
            test_urls = [u.strip() for u in urls_raw.split(",") if u.strip()] or ["http://example.com"]
            payload = {
                "proxies": proxies,
                "test_urls": test_urls,
                "timeout": 10,
                "check_anonymity": False,
                "check_geolocation": False,
                "concurrent_tests": 20,
                "test_all_urls": True,
            }
            self._status_text.set("Validando proxies...")
            try:
                r = requests.post(url, json=payload, headers=headers, timeout=30)
                if r.status_code == 429:
                    retry_after = r.headers.get("Retry-After") or r.headers.get("X-RateLimit-Reset")
                    self._status_text.set("Rate limit excedido na validação")
                    self.scheduler_text.delete("1.0", "end")
                    self.scheduler_text.insert("end", f"429 Too Many Requests. Tente novamente em: {retry_after} s\n")
                    return
                if r.status_code != 200:
                    self._status_text.set(f"Falha na validação: {r.status_code}")
                    self.scheduler_text.delete("1.0", "end")
                    self.scheduler_text.insert("end", f"Erro ao validar: HTTP {r.status_code}\n{r.text[:500]}")
                    return
                data = r.json()
            except Exception as e:
                self._status_text.set("Erro na validação")
                self.scheduler_text.delete("1.0", "end")
                self.scheduler_text.insert("end", f"Exceção: {e}")
                return

            # Exibir resumo e algumas linhas de resultado
            lines = []
            lines.append("=== Resultado da Validação ===")
            lines.append(f"success: {data.get('success')}")
            lines.append(f"total_tested: {data.get('total_tested')}")
            lines.append(f"valid_proxies: {data.get('valid_proxies')} | invalid_proxies: {data.get('invalid_proxies')}")
            lines.append(f"execution_time_ms: {data.get('execution_time_ms')}")
            # Gráfico ASCII de taxa de sucesso
            try:
                total = data.get('total_tested') or 0
                valid = data.get('valid_proxies') or 0
                rate = (valid / total) if isinstance(total, int) and total > 0 else None
                if isinstance(rate, float):
                    bar_len = 20
                    filled = int(round(rate * bar_len))
                    bar = "#" * filled + "-" * (bar_len - filled)
                    lines.append(f"success_rate_chart: [{bar}] {round(rate*100,1)}%")
            except Exception:
                pass
            # Listar primeiros 10 resultados
            try:
                results = data.get('results') or []
                if results:
                    lines.append("")
                    lines.append("Resultados (top 10):")
                    for i, res in enumerate(results[:10], 1):
                        proxy = res.get('proxy')
                        valid = res.get('valid')
                        avg_ms = res.get('avg_response_time_ms')
                        lines.append(f"  {i}. {proxy} | valid={valid} | avg_ms={avg_ms}")
            except Exception:
                pass

            self.scheduler_text.delete("1.0", "end")
            self.scheduler_text.insert("end", "\n".join(lines))
            self._status_text.set("Validação concluída")
            try:
                self._save_ui_settings()
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _toggle_scheduler_autorefresh(self):
        self._scheduler_autorefresh = bool(self.scheduler_auto_refresh_check.get())
        if self._scheduler_autorefresh:
            # Iniciar loop de auto-refresh
            self._scheduler_tick()
        else:
            # Cancelar qualquer agendamento pendente
            try:
                if self._scheduler_after_id is not None:
                    self.after_cancel(self._scheduler_after_id)
                    self._scheduler_after_id = None
            except Exception:
                pass

    def _scheduler_tick(self):
        if not self._scheduler_autorefresh:
            return
        try:
            interval = int((self.scheduler_auto_refresh_interval.get() or "5000").strip())
        except Exception:
            interval = 5000
        # Atualiza status (rede em thread) e reprograma
        self._update_scheduler_status()
        try:
            self._scheduler_after_id = self.after(interval, self._scheduler_tick)
        except Exception:
            self._scheduler_after_id = None

    def _scheduler_set_enabled(self, enabled: bool):
        def worker():
            base = (self.base_url_entry.get() or "http://localhost:8000").strip().rstrip("/")
            url = f"{base}/api/v1/proxies/scheduler/update"
            self._status_text.set("Atualizando configuração do scheduler...")
            try:
                headers = self._build_auth_headers()
                r = requests.post(url, json={"enabled": enabled}, headers=headers, timeout=8)
                if r.status_code == 429:
                    retry_after = r.headers.get("Retry-After") or r.headers.get("X-RateLimit-Reset")
                    self._status_text.set("Rate limit excedido ao atualizar")
                    self.scheduler_text.delete("1.0", "end")
                    self.scheduler_text.insert("end", f"429 Too Many Requests. Tente novamente em: {retry_after} s\n")
                    return
                if r.status_code != 200:
                    self._status_text.set(f"Falha ao atualizar: {r.status_code}")
                    self.scheduler_text.delete("1.0", "end")
                    self.scheduler_text.insert("end", f"Erro ao atualizar scheduler: HTTP {r.status_code}\n{r.text[:500]}")
                    return
                # Sucesso: refletir novo status
                data = r.json()
                self.scheduler_text.delete("1.0", "end")
                self.scheduler_text.insert("end", f"Scheduler {'ligado' if data.get('enabled') else 'desligado'} | running={data.get('running')}\n")
                self._status_text.set("Configuração do scheduler atualizada")
                try:
                    self._save_ui_settings()
                except Exception:
                    pass
            except Exception as e:
                self._status_text.set("Erro ao atualizar scheduler")
                self.scheduler_text.delete("1.0", "end")
                self.scheduler_text.insert("end", f"Exceção: {e}")
                return
            # Atualiza status completo após mudança
            self._update_scheduler_status()

        threading.Thread(target=worker, daemon=True).start()

    # Persistência simples de configurações da UI
    def _settings_path(self) -> Path:
        p = Path("data") / "ui_settings.json"
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        return p

    def _load_ui_settings(self):
        p = self._settings_path()
        if not p.exists():
            return
        try:
            with p.open("r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            return
        # Aplicar valores
        if isinstance(cfg.get("base_url"), str):
            self.base_url_entry.delete(0, "end")
            self.base_url_entry.insert(0, cfg["base_url"])
        if isinstance(cfg.get("api_key"), str):
            self.api_key_entry.delete(0, "end")
            self.api_key_entry.insert(0, cfg["api_key"])
        if isinstance(cfg.get("bearer"), str):
            self.bearer_entry.delete(0, "end")
            self.bearer_entry.insert(0, cfg["bearer"])
        if isinstance(cfg.get("autorefresh_interval_ms"), int):
            self.scheduler_auto_refresh_interval.delete(0, "end")
            self.scheduler_auto_refresh_interval.insert(0, str(cfg["autorefresh_interval_ms"]))
        if bool(cfg.get("autorefresh", False)):
            self.scheduler_auto_refresh_check.select()
            self._toggle_scheduler_autorefresh()

    def _save_ui_settings(self):
        cfg = {
            "base_url": (self.base_url_entry.get() or "").strip(),
            "api_key": (self.api_key_entry.get() or "").strip(),
            "bearer": (self.bearer_entry.get() or "").strip(),
            "autorefresh": bool(self.scheduler_auto_refresh_check.get()),
            "autorefresh_interval_ms": int((self.scheduler_auto_refresh_interval.get() or "5000").strip() or 5000),
        }
        p = self._settings_path()
        try:
            with p.open("w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


def run():
    app = ProxyManagerApp()
    app.mainloop()


if __name__ == "__main__":
    run()