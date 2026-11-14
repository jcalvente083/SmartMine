#include "mqttservice.h"

#include <QDebug>
#include <QMqttTopicFilter>
#include <QMqttTopicName>

#include <utility>

MqttService::MqttService(const MqttConfig& config, QObject* parent)
    : IMessageBus(parent)
{
    m_client.setHostname(config.host);
    m_client.setPort(config.port);
    m_client.setClientId(config.clientId);

    m_reconnectTimer.setSingleShot(true);
    connect(&m_reconnectTimer, &QTimer::timeout, this, [this]() {
        m_client.connectToHost();
        });

    connect(&m_client, &QMqttClient::connected, this, &MqttService::onConnected);
    connect(&m_client, &QMqttClient::messageReceived, this, &MqttService::onMessageReceived);

    connect(&m_client, &QMqttClient::stateChanged, this,
        [this](QMqttClient::ClientState state) {
            if (state == QMqttClient::Disconnected) {
                onDisconnected();
            }
        });
}

MqttService::~MqttService()
{
    disconnect(&m_client, nullptr, this, nullptr);

    m_shuttingDown = true;
    m_reconnectTimer.stop();
    m_client.disconnectFromHost();
}

void MqttService::start()
{
    m_client.connectToHost();
}

void MqttService::subscribe(const QString& topicFilter)
{
    m_subscriptions.insert(topicFilter);

    if (isConnected()) {
        subscribeOnClient(topicFilter);
    }
}

void MqttService::unsubscribe(const QString& topicFilter)
{
    m_subscriptions.remove(topicFilter);

    if (isConnected()) {
        m_client.unsubscribe(QMqttTopicFilter(topicFilter));
    }
}

void MqttService::publish(const QString& topic, const QByteArray& payload, bool retained)
{
    if (!isConnected()) {
        qWarning().noquote() << "No se ha podido publicar en" << topic << "(sin conexión con el broker)";
        return;
    }

    const qint32 messageId = m_client.publish(QMqttTopicName(topic), payload, kQos, retained);
    if (messageId == -1) {
        qWarning().noquote() << "Error al publicar en" << topic;
    }
}

bool MqttService::isConnected() const
{
    return m_client.state() == QMqttClient::Connected;
}

void MqttService::onConnected()
{
    qDebug() << "Conectado al broker";

    m_reconnectDelayMs = kInitialReconnectDelayMs;

    for (const QString& filter : std::as_const(m_subscriptions)) {
        subscribeOnClient(filter);
    }

    emit connectionStateChanged(true);
}

void MqttService::onDisconnected()
{
    if (m_shuttingDown) {
        return;
    }

    qDebug() << "Desconectado del broker. Reintentando en" << m_reconnectDelayMs << "ms";

    emit connectionStateChanged(false);
    scheduleReconnect();
}

void MqttService::scheduleReconnect()
{
    m_reconnectTimer.start(m_reconnectDelayMs);
    m_reconnectDelayMs = qMin(m_reconnectDelayMs * 2, kMaxReconnectDelayMs);
}

void MqttService::subscribeOnClient(const QString& topicFilter)
{
    if (!m_client.subscribe(QMqttTopicFilter(topicFilter), kQos)) {
        qWarning().noquote() << "No se ha podido suscribir a" << topicFilter;
    }
}

void MqttService::onMessageReceived(const QByteArray& message, const QMqttTopicName& topic)
{
    emit messageReceived(topic.name(), message);
}
