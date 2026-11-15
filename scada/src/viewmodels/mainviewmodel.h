#pragma once

#include "models/role.h"

#include <QObject>
#include <QString>

class IMessageBus;
class SessionService;

class MainViewModel : public QObject
{
    Q_OBJECT
        Q_PROPERTY(bool connected READ isConnected NOTIFY connectedChanged)
        Q_PROPERTY(QString connectionText READ connectionText NOTIFY connectedChanged)
        Q_PROPERTY(QString roleName READ roleName NOTIFY roleChanged)

public:
    explicit MainViewModel(IMessageBus& messageBus, SessionService& session,
        QObject* parent = nullptr);

    bool isConnected() const;
    QString connectionText() const;
    QString roleName() const;
    bool canView(Module module) const;

signals:
    void connectedChanged(bool connected);
    void roleChanged();

private:
    IMessageBus& m_messageBus;
    SessionService& m_session;
};
