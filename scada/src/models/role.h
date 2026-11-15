#pragma once

#include <QString>
#include <array>

enum class Role {
    ShiftSupervisor,  
    Hse,              
    Maintenance,
    Logistics,
};

enum class Module {
    Maintenance,
    Environment,
    Safety,
    Logistics,
};

inline constexpr std::array<Role, 4> kAllRoles{
    Role::ShiftSupervisor, Role::Hse, Role::Maintenance, Role::Logistics,
};
