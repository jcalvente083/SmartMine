#pragma once

#include <QObject>
#include <QString>

class IMessageBus;

class MainViewModel : public QObject
{
    Q_OBJECT
        Q_PROPERTY(bool connected READ isConnected NOTIFY connectedChanged)
        Q_PROPERTY(QString connectionText READ connectionText NOTIFY connectedChanged)

public:
    explicit MainViewModel(IMessageBus& messageBus, QObject* parent = nullptr);

    bool isConnected() const;
    QString connectionText() const;

signals:
    void connectedChanged(bool connected);

private:
    IMessageBus& m_messageBus;
};
