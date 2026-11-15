#pragma once

#include "models/role.h"

#include <QList>
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
    void updateRoleView();

    MainViewModel& m_viewModel;

    QTabWidget* m_tabs = nullptr;
    QLabel* m_roleLabel = nullptr;
    QLabel* m_connectionLabel = nullptr;

    QList<Module> m_tabModules; 
};
