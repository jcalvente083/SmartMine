#pragma once

#include "imessagebus.h"

#include <QMqttClient>
#include <QSet>
#include <QString>
#include <QTimer>

struct MqttConfig
{
    QString host;
    quint16 port = 1883;
    QString clientId;
};

class MqttService : public IMessageBus
{
    Q_OBJECT

public:
    explicit MqttService(const MqttConfig& config, QObject* parent = nullptr);
    ~MqttService() override;

    void start();

    void subscribe(const QString& topicFilter) override;
    void unsubscribe(const QString& topicFilter) override;
    void publish(const QString& topic, const QByteArray& payload, bool retained) override;
    bool isConnected() const override;

private:
    void onConnected();
    void onDisconnected();
    void onMessageReceived(const QByteArray& message, const QMqttTopicName& topic);
    void scheduleReconnect();
    void subscribeOnClient(const QString& topicFilter);

    static constexpr int kInitialReconnectDelayMs = 1000;
    static constexpr int kMaxReconnectDelayMs = 30000;
    static constexpr quint8 kQos = 1;

    QMqttClient m_client;
    QSet<QString> m_subscriptions;
    QTimer m_reconnectTimer;
    int m_reconnectDelayMs = kInitialReconnectDelayMs;
    bool m_shuttingDown = false;
};
