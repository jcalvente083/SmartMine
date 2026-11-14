#pragma once

#include <QMainWindow>

class MainViewModel;
class QLabel;
class QTabWidget;

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    explicit MainWindow(MainViewModel& viewModel, QWidget* parent = nullptr);

private:
    void setupUi();
    void updateConnectionIndicator();

    MainViewModel& m_viewModel;
    QTabWidget* m_tabs = nullptr;
    QLabel* m_connectionLabel = nullptr;
};
