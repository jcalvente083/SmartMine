// =============================================================================
//  SmartMine SCADA: "Hola MQTT"
//  Cliente de consola que valida la cadena Visual Studio + Qt 6 + Qt MQTT:
//  se conecta al broker, se suscribe a smartmine/# e imprime cada mensaje.
// =============================================================================

#include <QCoreApplication>
#include <QDebug>
#include <QMqttClient>
#include <QMqttTopicFilter>
#include <QMqttTopicName>

namespace {

    // --- Configuración de la conexión --------------------------------------------
    constexpr auto    kBrokerHost = "localhost";
    constexpr quint16 kBrokerPort = 1883;
    constexpr auto    kClientId = "smartmine-scada-dev";
    constexpr auto    kTopicFilter = "smartmine/#";
    constexpr quint8  kQos = 1;

    // Traduce el estado del cliente a un texto legible
    QString stateToString(QMqttClient::ClientState state)
    {
        switch (state) {
        case QMqttClient::Disconnected: return QStringLiteral("Desconectado");
        case QMqttClient::Connecting:   return QStringLiteral("Conectando...");
        case QMqttClient::Connected:    return QStringLiteral("Conectado");
        }
        return QStringLiteral("Desconocido");
    }

} // namespace

int main(int argc, char* argv[])
{
    // Debe crearse antes que cualquier otro objeto de Qt
    QCoreApplication app(argc, argv);

    QMqttClient client;
    client.setHostname(kBrokerHost);
    client.setPort(kBrokerPort);
    client.setClientId(kClientId);

    // RF2: estado de la conexión
    QObject::connect(&client, &QMqttClient::stateChanged,
        [](QMqttClient::ClientState state) {
            qDebug().noquote() << "Estado:" << stateToString(state);
        });

    // RF3: errores de conexión
    QObject::connect(&client, &QMqttClient::errorChanged,
        [](QMqttClient::ClientError error) {
            if (error != QMqttClient::NoError) {
                qWarning() << "Error MQTT:" << error;
            }
        });

    // RF4: suscripción al conectar
    QObject::connect(&client, &QMqttClient::connected, [&client]() {
        const auto* subscription = client.subscribe(QMqttTopicFilter(kTopicFilter), kQos);
        if (!subscription) {
            qWarning().noquote() << "No se pudo suscribir a" << kTopicFilter;
            return;
        }
        qDebug().noquote() << "Suscrito a" << kTopicFilter;
        });

    // RF5: mensajes recibidos
    QObject::connect(&client, &QMqttClient::messageReceived,
        [](const QByteArray& message, const QMqttTopicName& topic) {
            qDebug().noquote() << QStringLiteral("[%1]").arg(topic.name()) << message;
        });

    client.connectToHost();
    return app.exec();
}