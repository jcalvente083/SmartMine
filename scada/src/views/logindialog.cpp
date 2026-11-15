#include "logindialog.h"

#include "models/permissionpolicy.h"

#include <QComboBox>
#include <QLabel>
#include <QPushButton>
#include <QVBoxLayout>

LoginDialog::LoginDialog(QWidget* parent)
    : QDialog(parent)
{
    setWindowTitle(QStringLiteral("SmartMine SCADA: inicio de sesión"));

    auto* title = new QLabel(QStringLiteral("Selecciona tu rol para continuar"));

    m_roleCombo = new QComboBox;
    m_roleCombo->setPlaceholderText(QStringLiteral("Selecciona un rol..."));

    for (Role role : kAllRoles) {
        const QString text = PermissionPolicy::roleDisplayName(role);
        const int data = static_cast<int>(role);
        m_roleCombo->addItem(text, data);
    }

    m_roleCombo->setCurrentIndex(-1);  // Ningún rol elegido al empezar

    m_enterButton = new QPushButton(QStringLiteral("Entrar"));
    m_enterButton->setDefault(true);
    m_enterButton->setEnabled(false);

    connect(m_roleCombo, &QComboBox::currentIndexChanged, this, [this](int index) {
        m_enterButton->setEnabled(index >= 0);
        });

    connect(m_enterButton, &QPushButton::clicked, this, &QDialog::accept);

    auto* layout = new QVBoxLayout(this);
    layout->addWidget(title);
    layout->addWidget(m_roleCombo);
    layout->addWidget(m_enterButton);
}

Role LoginDialog::selectedRole() const
{
    return static_cast<Role>(m_roleCombo->currentData().toInt());
}
