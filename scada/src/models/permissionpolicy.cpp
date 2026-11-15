#include "permissionpolicy.h"

namespace PermissionPolicy {

    QString roleDisplayName(Role role)
    {
        switch (role)
        {
        case Role::ShiftSupervisor: return "Jefe de Turno";
        case Role::Hse:             return "SSMA";
        case Role::Maintenance:     return "Mantenimiento";
        case Role::Logistics:       return "Logística";
        default:                    return QStringLiteral("Desconocido");
        }
    }

    bool canView(Role role, Module module)
    {
        
        switch (role)
        {
        case Role::ShiftSupervisor: return true;
        case Role::Hse:             return module == Module::Environment || module == Module::Safety;
        case Role::Maintenance:     return module == Module::Maintenance;
        case Role::Logistics:       return module == Module::Logistics;
        default:                    return false;
        }
    }

    bool canReset(Role role)
    {
        
        return role == Role::ShiftSupervisor;
    }

} // namespace PermissionPolicy
