#pragma once

#include "role.h"

#include <QString>

namespace PermissionPolicy {

    QString roleDisplayName(Role role);
    bool canView(Role role, Module module);
    bool canReset(Role role);

} // namespace PermissionPolicy
