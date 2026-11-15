#include "emergencyviewmodel.h"

#include "models/permissionpolicy.h"
#include "services/imessagebus.h"
#include "services/sessionservice.h"

#include <QDateTime>
#include <QDebug>
#include <QJsonDocument>
#include <QJsonObject>
#include <QUuid>

namespace {

    constexpr auto kEmergencyTopic = "smartmine/global/all/comando";
    constexpr auto kOrigin = "scada_dashboard";

} // namespace

EmergencyViewModel::EmergencyViewModel(IMessageBus& messageBus, SessionService& session,
    QObject* parent)
    : QObject(parent)
    , m_messageBus(messageBus)
    , m_session(session)
{
    connect(&m_messageBus, &IMessageBus::messageReceived, this, &EmergencyViewModel::onMessageReceived);

    connect(&m_session, &SessionService::roleChanged, this, &EmergencyViewModel::canResetChanged);

    m_messageBus.subscribe(QLatin1String(kEmergencyTopic));
}

bool EmergencyViewModel::isEmergencyActive() const
{
    return m_emergencyActive;
}

bool EmergencyViewModel::canReset() const
{
    return PermissionPolicy::canReset(m_session.role()) && m_emergencyActive;
}

void EmergencyViewModel::triggerEmergencyStop()
{
    publishCommand(QStringLiteral("estop"));
}

void EmergencyViewModel::resetEmergency()
{
    if (!canReset()) {
        qWarning() << "El rol activo no tiene permiso de rearme";
        return;
    }
    publishCommand(QStringLiteral("reset"));
}

void EmergencyViewModel::onMessageReceived(const QString& topic, const QByteArray& payload)
{
    if (topic != QLatin1String(kEmergencyTopic)) {
        return;
    }

    const QString command = QJsonDocument::fromJson(payload).object()
        .value(QStringLiteral("comando")).toString();

    if (command == QLatin1String("estop")) {
        setEmergencyActive(true);
    }
    else if (command == QLatin1String("reset")) {
        setEmergencyActive(false);
    }
}

void EmergencyViewModel::setEmergencyActive(bool active)
{
    if (m_emergencyActive == active) {
        return;
    }

    m_emergencyActive = active;
    emit emergencyActiveChanged(active);
    emit canResetChanged();  
}

void EmergencyViewModel::publishCommand(const QString& command)
{
    const QJsonObject message{
        { QStringLiteral("command_id"), QUuid::createUuid().toString(QUuid::WithoutBraces) },
        { QStringLiteral("timestamp"), QDateTime::currentMSecsSinceEpoch() },
        { QStringLiteral("comando"), command },
        { QStringLiteral("origen"), QLatin1String(kOrigin) },
    };

    m_messageBus.publish(QLatin1String(kEmergencyTopic),
        QJsonDocument(message).toJson(QJsonDocument::Compact),
        true);
}
