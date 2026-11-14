#include "mainwindow.h"

#include "viewmodels/mainviewmodel.h"

#include <QLabel>
#include <QStatusBar>
#include <QTabWidget>
#include <QStyle>

MainWindow::MainWindow(MainViewModel& viewModel, QWidget* parent)
    : QMainWindow(parent)
    , m_viewModel(viewModel)
{
    setupUi();

    connect(&m_viewModel, &MainViewModel::connectedChanged, this, &MainWindow::updateConnectionIndicator);

    updateConnectionIndicator();
}

void MainWindow::setupUi()
{
    setWindowTitle(QStringLiteral("SmartMine SCADA"));
    resize(1280, 800);

    m_tabs = new QTabWidget(this);
    m_tabs->addTab(new QLabel(QStringLiteral("Próximamente")), QStringLiteral("Mantenimiento"));
    m_tabs->addTab(new QLabel(QStringLiteral("Próximamente")), QStringLiteral("Medio Ambiente"));
    m_tabs->addTab(new QLabel(QStringLiteral("Próximamente")), QStringLiteral("Seguridad"));
    m_tabs->addTab(new QLabel(QStringLiteral("Próximamente")), QStringLiteral("Logística"));
    setCentralWidget(m_tabs);

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
