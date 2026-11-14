// =============================================================================
//  SmartMine SCADA: raíz de composición
//  Crea los servicios, los ViewModels y las vistas, y los conecta entre sí.
// =============================================================================

#include "services/mqttservice.h"
#include "viewmodels/mainviewmodel.h"
#include "views/mainwindow.h"

#include <QApplication>
#include <QFile>
#include <QDebug>

namespace {

    // --- Configuración de la conexión --------------------------------------------
    constexpr auto    kBrokerHost = "localhost";
    constexpr quint16 kBrokerPort = 1883;
    constexpr auto    kClientId = "smartmine-scada-dev";

} // namespace

int main(int argc, char* argv[])
{
    QApplication app(argc, argv);

    QFile styleFile(QStringLiteral(":/styles/dark.qss"));
if (styleFile.open(QIODevice::ReadOnly | QIODevice::Text)) {
    app.setStyleSheet(QString::fromUtf8(styleFile.readAll()));
} else {
    qWarning() << "No se ha podido cargar la hoja de estilo";
}

    MqttService mqttService(MqttConfig{ kBrokerHost, kBrokerPort, kClientId });
    MainViewModel mainViewModel(mqttService);
    MainWindow mainWindow(mainViewModel);

    mainWindow.show();
    mqttService.start();

    return app.exec();
}
