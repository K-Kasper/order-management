import multiprocessing

from order_management.ui.main_window import MainWindow


def main() -> None:
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
