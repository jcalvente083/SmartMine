#pragma once

#include <QByteArray>
#include <QObject>
#include <QString>

class IMessageBus : public QObject
{
    Q_OBJECT

public:
    explicit IMessageBus(QObject* parent = nullptr) : QObject(parent) {}
    ~IMessageBus() override = default;


    virtual void subscribe(const QString& topicFilter) = 0;

    virtual void unsubscribe(const QString& topicFilter) = 0;

    virtual void publish(const QString& topic, const QByteArray& payload, bool retained) = 0;

    virtual bool isConnected() const = 0;

signals:
    void messageReceived(const QString& topic, const QByteArray& payload);

    void connectionStateChanged(bool connected);
};