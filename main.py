
                return self.send_json(200, {
                    "ok": True,
                    "ins_code": ins_code,
                    "symbol": symbol["symbol"],
                    "fetched_records": len(records),
                    "saved_records": total,
                    "latest_trade_date": latest
                })

            # ذخیره پیام‌های گفتگو
            if path == "/api/chat":
                message = str(
                    payload.get("message", "")
                ).strip()

                if not message:
                    return self.send_json(400, {
                        "ok": False,
                        "error": "پیام خالی است."
                    })

                if len(message) > MAX_MESSAGE:
                    return self.send_json(413, {
                        "ok": False,
                        "error": "طول پیام بیش از حد مجاز است."
                    })

                save_message("user", message)

                reply = (
                    "پیام شما در BEHZAD AI ذخیره شد. "
                    "موتور تحلیل تخصصی بازار در حال توسعه است."
                )

                save_message("assistant", reply)

                return self.send_json(200, {
                    "ok": True,
                    "reply": reply
                })

            # ذخیره تنظیمات
            if path == "/api/settings":
                settings = payload.get("settings", {})

                if not isinstance(settings, dict):
                    return self.send_json(400, {
                        "ok": False,
                        "error": "ساختار تنظیمات نامعتبر است."
                    })

                with DB_LOCK, connect_db() as con:
                    for key, value in settings.items():
                        con.execute("""
                            INSERT INTO settings(
                                key, value, updated_at
                            )
                            VALUES(?,?,?)
                            ON CONFLICT(key)
                            DO UPDATE SET
                                value=excluded.value,
                                updated_at=excluded.updated_at
                        """, (
                            str(key),
                            json.dumps(
                                value,
                                ensure_ascii=False
                            ),
                            now_iso()
                        ))
                    con.commit()

                return self.send_json(200, {
                    "ok": True,
                    "saved": len(settings)
                })

            # ایجاد نسخه پشتیبان
            if path == "/api/backup":
                target = make_backup()

                return self.send_json(200, {
                    "ok": True,
                    "backup": target.name,
                    "size": target.stat().st_size
                })

            # بازیابی نسخه پشتیبان
            if path == "/api/restore":
                name = str(
                    payload.get("name", "")
                ).strip()

                if (
                    not name
                    or Path(name).name != name
                    or not name.endswith(".sqlite3")
                ):
                    return self.send_json(400, {
                        "ok": False,
                        "error": "نام فایل پشتیبان نامعتبر است."
                    })

                source_path = BACKUPS / name

                if not source_path.is_file():
                    return self.send_json(404, {
                        "ok": False,
                        "error": "فایل پشتیبان پیدا نشد."
                    })

                make_backup()

                with DB_LOCK:
                    source = sqlite3.connect(source_path)
                    destination = connect_db()

                    try:
                        source.backup(destination)
                    finally:
                        source.close()
                        destination.close()

                init_db()

                return self.send_json(200, {
                    "ok": True,
                    "restored": name
                })

            return self.send_json(404, {
                "ok": False,
                "error": "مسیر درخواست‌شده پیدا نشد."
            })

        except ValueError as exc:
            return self.send_json(400, {
                "ok": False,
                "error": str(exc)
            })

        except Exception as exc:
            return self.send_json(500, {
                "ok": False,
                "error": str(exc)
            })

    def log_message(self, fmt, *args):
        print(
            "[%s] %s" % (
                self.log_date_time_string(),
                fmt % args
            ),
            flush=True
        )


def run():
    init_db()

    port = int(os.environ.get("PORT", "10000"))

    server = ThreadingHTTPServer(
        ("0.0.0.0", port),
        Handler
    )

    print(
        f"BEHZAD AI {VERSION} running on port {port}",
        flush=True
    )

    server.serve_forever()


if __name__ == "__main__":
    run()
