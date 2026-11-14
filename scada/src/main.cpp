// =============================================================================
//  SmartMine SCADA: raíz de composición
//  Crea los servicios, los ViewModels y las vistas, y los conecta entre sí.
// =============================================================================

#include "services/mqttservice.h"
#include "viewmodels/mainviewmodel.h"
#include "views/mainwindow.h"

#include <QApplication>

namespace {

    // --- Configuración de la conexión --------------------------------------------
    constexpr auto    kBrokerHost = "localhost";
    constexpr quint16 kBrokerPort = 1883;
    constexpr auto    kClientId = "smartmine-scada-dev";

} // namespace

int main(int argc, char* argv[])
{
    QApplication app(argc, argv);

    MqttService mqttService(MqttConfig{ kBrokerHost, kBrokerPort, kClientId });
    MainViewModel mainViewModel(mqttService);
    MainWindow mainWindow(mainViewModel);

    mainWindow.show();
    mqttService.start();

    return app.exec();
}
