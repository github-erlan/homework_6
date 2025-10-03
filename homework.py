import sys, os, sqlite3
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QSpinBox, QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QCheckBox, QMessageBox, QStatusBar
)
from PyQt6.QtCore import Qt

DB_FILE = "shopping.db"

# --- Фикс для macOS, чтобы Qt не падал ---
import PyQt6.QtCore as QtCore
plugin_path = os.path.join(os.path.dirname(QtCore.__file__), "Qt6", "plugins", "platforms")
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = plugin_path


class ShoppingApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Список покупок")
        self.resize(600, 400)

        self.conn = sqlite3.connect(DB_FILE)
        self.create_table()

        layout = QVBoxLayout(self)

        # --- Поля ввода ---
        input_layout = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Название")
        self.qty_input = QSpinBox()
        self.qty_input.setRange(1, 99)
        self.qty_input.setValue(1)

        self.category_input = QComboBox()
        self.category_input.addItems(["Овощи", "Молочные", "Бытовое", "Другое"])
        self.priority_input = QComboBox()
        self.priority_input.addItems(["Низкий", "Средний", "Высокий"])

        input_layout.addWidget(self.name_input)
        input_layout.addWidget(self.qty_input)
        input_layout.addWidget(self.category_input)
        input_layout.addWidget(self.priority_input)

        # --- Кнопки ---
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Добавить")
        self.update_btn = QPushButton("Обновить")
        self.delete_btn = QPushButton("Удалить")
        self.toggle_btn = QPushButton("Отметить купленным")
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.update_btn)
        btn_layout.addWidget(self.delete_btn)
        btn_layout.addWidget(self.toggle_btn)

        # --- Таблица ---
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Название", "Кол-во", "Категория", "Приоритет", "Куплено ✔"])
        self.table.setColumnWidth(0, 200)

        # --- Статус-бар ---
        self.status_bar = QStatusBar()

        layout.addLayout(input_layout)
        layout.addLayout(btn_layout)
        layout.addWidget(self.table)
        layout.addWidget(self.status_bar)

        # --- Сигналы ---
        self.add_btn.clicked.connect(self.add_item)
        self.update_btn.clicked.connect(self.update_item)
        self.delete_btn.clicked.connect(self.delete_item)
        self.toggle_btn.clicked.connect(self.toggle_bought)
        self.table.cellClicked.connect(self.fill_inputs)

        self.load_items()

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            qty INT,
            category TEXT,
            priority TEXT,
            bought INT DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        self.conn.commit()

    def load_items(self):
        self.table.setRowCount(0)
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, name, qty, category, priority, bought FROM items")
        for row_data in cursor.fetchall():
            self.add_table_row(row_data)
        self.update_status()

    def add_table_row(self, row_data):
        row = self.table.rowCount()
        self.table.insertRow(row)
        for col, val in enumerate(row_data[1:5]):
            self.table.setItem(row, col, QTableWidgetItem(str(val)))
        chk = QCheckBox()
        chk.setChecked(bool(row_data[5]))
        chk.setEnabled(False)
        self.table.setCellWidget(row, 4, chk)
        self.table.setRowHeight(row, 25)

    def add_item(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Название не может быть пустым")
            return
        qty = self.qty_input.value()
        category = self.category_input.currentText()
        priority = self.priority_input.currentText()
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO items (name, qty, category, priority) VALUES (?, ?, ?, ?)",
                       (name, qty, category, priority))
        self.conn.commit()
        self.load_items()
        self.clear_inputs()

    def update_item(self):
        row = self.table.currentRow()
        if row == -1:
            return
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Название не может быть пустым")
            return
        qty = self.qty_input.value()
        category = self.category_input.currentText()
        priority = self.priority_input.currentText()
        item_id = self.get_item_id(row)
        cursor = self.conn.cursor()
        cursor.execute("UPDATE items SET name=?, qty=?, category=?, priority=? WHERE id=?",
                       (name, qty, category, priority, item_id))
        self.conn.commit()
        self.load_items()

    def delete_item(self):
        row = self.table.currentRow()
        if row == -1:
            return
        reply = QMessageBox.question(self, "Подтверждение", "Удалить выбранный элемент?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            item_id = self.get_item_id(row)
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM items WHERE id=?", (item_id,))
            self.conn.commit()
            self.load_items()

    def toggle_bought(self):
        row = self.table.currentRow()
        if row == -1:
            return
        item_id = self.get_item_id(row)
        chk = self.table.cellWidget(row, 4)
        new_state = 0 if chk.isChecked() else 1
        cursor = self.conn.cursor()
        cursor.execute("UPDATE items SET bought=? WHERE id=?", (new_state, item_id))
        self.conn.commit()
        self.load_items()

    def get_item_id(self, row):
        cursor = self.conn.cursor()
        name = self.table.item(row, 0).text()
        qty = int(self.table.item(row, 1).text())
        cursor.execute("SELECT id FROM items WHERE name=? AND qty=? ORDER BY created_at DESC LIMIT 1", (name, qty))
        return cursor.fetchone()[0]

    def fill_inputs(self, row, _col):
        self.name_input.setText(self.table.item(row, 0).text())
        self.qty_input.setValue(int(self.table.item(row, 1).text()))
        self.category_input.setCurrentText(self.table.item(row, 2).text())
        self.priority_input.setCurrentText(self.table.item(row, 3).text())

    def clear_inputs(self):
        self.name_input.clear()
        self.qty_input.setValue(1)
        self.category_input.setCurrentIndex(0)
        self.priority_input.setCurrentIndex(0)

    def update_status(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM items")
        total = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM items WHERE bought=1")
        bought = cursor.fetchone()[0]
        self.status_bar.showMessage(f"Всего: {total} | Куплено: {bought} | Осталось: {total - bought}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ShoppingApp()
    window.show()
    sys.exit(app.exec())
