#include "sessionservice.h"

SessionService::SessionService(Role initialRole, QObject* parent)
    : QObject(parent)
    , m_role(initialRole)
{
}

Role SessionService::role() const
{
    return m_role;
}

void SessionService::setRole(Role role)
{
    if (m_role == role) {
        return;
    }

    m_role = role;
    emit roleChanged(m_role);
}
