#pragma once

#include "models/role.h"

#include <QObject>

class SessionService : public QObject
{
    Q_OBJECT

public:
    explicit SessionService(Role initialRole, QObject* parent = nullptr);

    Role role() const;
    void setRole(Role role);

signals:
    void roleChanged(Role role);

private:
    Role m_role;
};

