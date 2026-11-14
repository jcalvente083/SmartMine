#include "mainviewmodel.h"

#include "services/imessagebus.h"

MainViewModel::MainViewModel(IMessageBus& messageBus, QObject* parent)
    : QObject(parent)
    , m_messageBus(messageBus)
{
    connect(&m_messageBus, &IMessageBus::connectionStateChanged, this, &MainViewModel::connectedChanged);
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




