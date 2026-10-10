import argparse
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from main_window import MainWindow
from parser import Parser
from refactorizer import Refactorizer
from tokenizator import Tokenizator
from PyQt6.QtWidgets import QApplication
#==============================================================================================================================================================================================================================================================
# Main.py - точка входа, Qt интерфейс с возможностью загрузки csv и выгрузки токенов и общая организация.
# Авторство: Шагиев Д. Ю. МТ-201 и Лонщаков А. К. МТ-201
#==============================================================================================================================================================================================================================================================
def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 9))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
