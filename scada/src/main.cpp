// =============================================================================
//  SmartMine SCADA: raíz de composición (provisional, en consola)
//  Crea el MqttService, se suscribe a smartmine/# e imprime cada mensaje.
//  La reconexión automática es responsabilidad del servicio.
// =============================================================================

#include "services/mqttservice.h"

#include <QCoreApplication>
#include <QDebug>

namespace {

    // --- Configuración de la conexión --------------------------------------------
    constexpr auto    kBrokerHost = "localhost";
    constexpr quint16 kBrokerPort = 1883;
    constexpr auto    kClientId = "smartmine-scada-dev";
    constexpr auto    kTopicFilter = "smartmine/#";

} // namespace

int main(int argc, char* argv[])
{
    QCoreApplication app(argc, argv);

    const MqttConfig config{ kBrokerHost, kBrokerPort, kClientId };
    MqttService mqttService(config);

    QObject::connect(&mqttService, &IMessageBus::connectionStateChanged,
        [](bool connected) {
            qDebug() << (connected ? "Estado: conectado" : "Estado: desconectado");
        });

    QObject::connect(&mqttService, &IMessageBus::messageReceived,
        [](const QString& topic, const QByteArray& payload) {
            qDebug().noquote() << QStringLiteral("[%1]").arg(topic) << payload;
        });

    mqttService.subscribe(kTopicFilter);
    mqttService.start();

    return app.exec();
}
