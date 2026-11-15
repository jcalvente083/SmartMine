#include "mainwindow.h"

#include "viewmodels/emergencyviewmodel.h"
#include "viewmodels/mainviewmodel.h"
#include "views/logindialog.h"

#include <QCloseEvent>
#include <QHBoxLayout>
#include <QLabel>
#include <QMessageBox>
#include <QPushButton>
#include <QScreen>
#include <QStatusBar>
#include <QStyle>
#include <QTabWidget>
#include <QVBoxLayout>

MainWindow::MainWindow(MainViewModel& viewModel, EmergencyViewModel& emergencyViewModel,
    QWidget* parent)
    : QMainWindow(parent)
    , m_viewModel(viewModel)
    , m_emergencyViewModel(emergencyViewModel)
{
    setupUi();

    connect(&m_viewModel, &MainViewModel::connectedChanged, this, &MainWindow::updateConnectionIndicator);
    connect(&m_viewModel, &MainViewModel::roleChanged, this, &MainWindow::updateRoleView);

    connect(m_emergencyStopButton, &QPushButton::clicked,
        &m_emergencyViewModel, &EmergencyViewModel::triggerEmergencyStop);
    connect(m_resetButton, &QPushButton::clicked, this, &MainWindow::confirmReset);
    connect(&m_emergencyViewModel, &EmergencyViewModel::emergencyActiveChanged,
        this, &MainWindow::updateEmergencyView);
    connect(&m_emergencyViewModel, &EmergencyViewModel::canResetChanged,
        this, &MainWindow::updateEmergencyView);

    connect(m_switchUserButton, &QPushButton::clicked, this, [this]() {
        LoginDialog dialog(this);
        if (dialog.exec() == QDialog::Accepted) {
            m_viewModel.changeRole(dialog.selectedRole());
        }
        });

    updateConnectionIndicator();
    updateRoleView();
    updateEmergencyView();
}

void MainWindow::setupUi()
{
    setWindowTitle(QStringLiteral("SmartMine SCADA"));

    const QRect available = screen()->availableGeometry();
    resize(available.size() * 0.8);
    move(available.center() - rect().center());

    m_tabs = new QTabWidget(this);

    m_tabs->addTab(new QLabel(QStringLiteral("Próximamente")), QStringLiteral("Mantenimiento"));
    m_tabModules.append(Module::Maintenance);

    m_tabs->addTab(new QLabel(QStringLiteral("Próximamente")), QStringLiteral("Medio Ambiente"));
    m_tabModules.append(Module::Environment);

    m_tabs->addTab(new QLabel(QStringLiteral("Próximamente")), QStringLiteral("Seguridad"));
    m_tabModules.append(Module::Safety);

    m_tabs->addTab(new QLabel(QStringLiteral("Próximamente")), QStringLiteral("Logística"));
    m_tabModules.append(Module::Logistics);

    auto* central = new QWidget(this);
    auto* centralLayout = new QVBoxLayout(central);
    centralLayout->addWidget(createEmergencyBar());
    centralLayout->addWidget(m_tabs);
    setCentralWidget(central);

    m_switchUserButton = new QPushButton(QStringLiteral("Cambiar de usuario"), this);
    statusBar()->addPermanentWidget(m_switchUserButton);

    m_roleLabel = new QLabel(this);
    statusBar()->addPermanentWidget(m_roleLabel);

    m_connectionLabel = new QLabel(this);
    m_connectionLabel->setObjectName(QStringLiteral("connectionIndicator"));
    statusBar()->addPermanentWidget(m_connectionLabel);
}

QWidget* MainWindow::createEmergencyBar()
{
    auto* bar = new QWidget;

    m_emergencyStopButton = new QPushButton(QStringLiteral("PARADA DE EMERGENCIA"));
    m_emergencyStopButton->setObjectName(QStringLiteral("emergencyStopButton"));

    m_emergencyBanner = new QLabel(QStringLiteral("⚠ PARADA DE EMERGENCIA ACTIVA"));
    m_emergencyBanner->setObjectName(QStringLiteral("emergencyBanner"));

    m_resetButton = new QPushButton(QStringLiteral("Rearmar"));

    auto* layout = new QHBoxLayout(bar);
    layout->addWidget(m_emergencyStopButton);
    layout->addWidget(m_emergencyBanner, 1);  
    layout->addWidget(m_resetButton);

    return bar;
}

void MainWindow::updateConnectionIndicator()
{
    m_connectionLabel->setText(m_viewModel.connectionText());

    m_connectionLabel->setProperty("connected", m_viewModel.isConnected());
    style()->unpolish(m_connectionLabel);
    style()->polish(m_connectionLabel);
}

void MainWindow::updateRoleView()
{
    m_roleLabel->setText(QStringLiteral("Rol: %1").arg(m_viewModel.roleName()));

    for (int i = 0; i < m_tabModules.size(); ++i) {
        m_tabs->setTabVisible(i, m_viewModel.canView(m_tabModules[i]));
    }
}

void MainWindow::updateEmergencyView()
{
    const bool active = m_emergencyViewModel.isEmergencyActive();
    const bool canReset = m_emergencyViewModel.canReset();

    m_emergencyBanner->setVisible(active);
    m_resetButton->setVisible(active);
    m_resetButton->setEnabled(canReset);
    m_resetButton->setToolTip(canReset ? QString()
        : QStringLiteral("Solo el Jefe de Turno puede rearmar"));
}

void MainWindow::confirmReset()
{
    const auto answer = QMessageBox::question(
        this,
        QStringLiteral("Rearmar parada de emergencia"),
        QStringLiteral("¿Has verificado que la causa de la emergencia está resuelta\n"
            "y que la zona es segura para reanudar la operación?"),
        QMessageBox::Yes | QMessageBox::No,
        QMessageBox::No);

    if (answer == QMessageBox::Yes) {
        m_emergencyViewModel.resetEmergency();
    }
}

void MainWindow::closeEvent(QCloseEvent* event)
{
    const auto answer = QMessageBox::question(
        this,
        QStringLiteral("Salir de SmartMine SCADA"),
        QStringLiteral("¿Seguro que quieres cerrar el SCADA?\n"
            "Se dejará de supervisar la operación."),
        QMessageBox::Yes | QMessageBox::No,
        QMessageBox::No);

    if (answer == QMessageBox::Yes) {
        event->accept();
    }
    else {
        event->ignore();
    }
}
