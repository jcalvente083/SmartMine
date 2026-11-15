#pragma once

#include "models/role.h"

#include <QDialog>

class QComboBox;
class QPushButton;

class LoginDialog : public QDialog
{
    Q_OBJECT

public:
    explicit LoginDialog(QWidget* parent = nullptr);

    Role selectedRole() const;

private:
    QComboBox* m_roleCombo = nullptr;
    QPushButton* m_enterButton = nullptr;
};
