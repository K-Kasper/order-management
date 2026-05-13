# BP Order Management

A desktop order management system for tracking customer orders, managing order statuses, and generating PDF reports. Built with Python and Tkinter.

## Run It

Install dependencies:

```bash
uv sync
```

Run the application:

```bash
uv run order-management
```

## Build An Executable

Install dev tools:

```bash
uv sync --group dev
```

The project has a PyInstaller spec:

```bash
uv run pyinstaller --noconfirm BP-Order-Management.spec
```

Output goes to `dist/`.

## Demo Data

Use **Tools > Seed Demo Data** to fill an empty database with sample customers and
orders.

## Where Data Goes

Typical Linux paths:

- Database: `~/.local/share/bp-order-management/order_management.sqlite3`
- Uploaded images: `~/.local/share/bp-order-management/uploads/`
- Settings: `~/.local/share/bp-order-management/settings.json`

## Checks

Lint:

```bash
uv run ruff check .
```

Format check:

```bash
uv run ruff format --check .
```

Format:

```bash
uv run ruff format .
```

## License

This project is licensed under the [AGPL-3.0](LICENSE).
