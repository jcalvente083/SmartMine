#include "mainviewmodel.h"

#include "services/imessagebus.h"
#include "models/permissionpolicy.h"
#include "services/sessionservice.h"

MainViewModel::MainViewModel(IMessageBus& messageBus, SessionService& session, QObject* parent)
    : QObject(parent)
    , m_messageBus(messageBus)
    , m_session(session)
{
    connect(&m_messageBus, &IMessageBus::connectionStateChanged, this, &MainViewModel::connectedChanged);
    connect(&m_session, &SessionService::roleChanged, this, &MainViewModel::roleChanged);
}

bool MainViewModel::isConnected() const
{
    return m_messageBus.isConnected();
}

QString MainViewModel::connectionText() const
{
    return isConnected() ? QStringLiteral("Conectado al broker")
        : QStringLiteral("Sin conexión: datos no actualizados");
}

QString MainViewModel::roleName() const
{
    return PermissionPolicy::roleDisplayName(m_session.role());
}

bool MainViewModel::canView(Module module) const
{
    return PermissionPolicy::canView(m_session.role(), module);
    
}

void MainViewModel::changeRole(Role role)
{
    m_session.setRole(role);
}
