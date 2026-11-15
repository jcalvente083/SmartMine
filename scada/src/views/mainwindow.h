#pragma once

#include "models/role.h"

#include <QList>
#include <QMainWindow>

class EmergencyViewModel;
class MainViewModel;
class QLabel;
class QPushButton;
class QTabWidget;



class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    explicit MainWindow(MainViewModel& viewModel, EmergencyViewModel& emergencyViewModel,
        QWidget* parent = nullptr);

protected:
    void closeEvent(QCloseEvent* event) override;

private:
    void setupUi();
    void updateConnectionIndicator();
    void updateRoleView();
    QWidget* createEmergencyBar();
    void updateEmergencyView();
    void confirmReset();

    MainViewModel& m_viewModel;
    EmergencyViewModel& m_emergencyViewModel;

    QTabWidget* m_tabs = nullptr;
    QLabel* m_roleLabel = nullptr;
    QLabel* m_connectionLabel = nullptr;
    QPushButton* m_switchUserButton = nullptr;
    QPushButton* m_emergencyStopButton = nullptr;
    QLabel* m_emergencyBanner = nullptr;
    QPushButton* m_resetButton = nullptr;

    QList<Module> m_tabModules; 
};
