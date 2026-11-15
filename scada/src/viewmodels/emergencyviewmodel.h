#pragma once

#include <QObject>
#include <QString>

class IMessageBus;
class SessionService;

class EmergencyViewModel : public QObject
{
    Q_OBJECT
        Q_PROPERTY(bool emergencyActive READ isEmergencyActive NOTIFY emergencyActiveChanged)
        Q_PROPERTY(bool canReset READ canReset NOTIFY canResetChanged)

public:
    explicit EmergencyViewModel(IMessageBus& messageBus, SessionService& session,
        QObject* parent = nullptr);

    bool isEmergencyActive() const;
    bool canReset() const;

    void triggerEmergencyStop();
    void resetEmergency();

signals:
    void emergencyActiveChanged(bool active);
    void canResetChanged();

private:
    void onMessageReceived(const QString& topic, const QByteArray& payload);
    void setEmergencyActive(bool active);
    void publishCommand(const QString& command);

    IMessageBus& m_messageBus;
    SessionService& m_session;
    bool m_emergencyActive = false;
};
