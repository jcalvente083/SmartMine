#include "mainwindow.h"

#include "viewmodels/mainviewmodel.h"
#include "views/logindialog.h"

#include <QLabel>
#include <QPushButton>
#include <QStatusBar>
#include <QStyle>
#include <QScreen>
#include <QTabWidget>

MainWindow::MainWindow(MainViewModel& viewModel, QWidget* parent)
    : QMainWindow(parent)
    , m_viewModel(viewModel)
{
    setupUi();

    connect(&m_viewModel, &MainViewModel::connectedChanged, this, &MainWindow::updateConnectionIndicator);
    connect(&m_viewModel, &MainViewModel::roleChanged, this, &MainWindow::updateRoleView);
    connect(m_switchUserButton, &QPushButton::clicked, this, [this]() {
        LoginDialog dialog(this);
        if (dialog.exec() == QDialog::Accepted) {
            m_viewModel.changeRole(dialog.selectedRole());
        }
        });

    updateConnectionIndicator();
    updateRoleView();
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

    setCentralWidget(m_tabs);

    m_switchUserButton = new QPushButton(QStringLiteral("Cambiar de usuario"), this);
    statusBar()->addPermanentWidget(m_switchUserButton);

    m_roleLabel = new QLabel(this);
    statusBar()->addPermanentWidget(m_roleLabel);

    m_connectionLabel = new QLabel(this);
    m_connectionLabel->setObjectName(QStringLiteral("connectionIndicator"));
    statusBar()->addPermanentWidget(m_connectionLabel);
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
