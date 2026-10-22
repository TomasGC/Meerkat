class ExportPlugin:
    """Extension point for future export formats."""

    def before_write(self, rows):
        return rows


def export_csv(rows, path, plugins=(ExportPlugin(),)):
    for plugin in plugins:
        rows = plugin.before_write(rows)
    with open(path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(",".join(str(v) for v in row) + "\n")


if __name__ == "__main__":
    export_csv([(1, "a")], "out.csv")
