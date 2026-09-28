using System;
using System.Collections.Generic;

namespace LotusApi.Models;

public partial class DimEmployee
{
    public string? EmployeeId { get; set; }

    public string? FirstName { get; set; }

    public string? LastName { get; set; }

    public string? Gender { get; set; }

    public string? Role { get; set; }

    public long? StoreId { get; set; }

    public string? HireDate { get; set; }

    public long? MonthlySalaryEgp { get; set; }

    public string? BatchId { get; set; }

    public string? AttributeHash { get; set; }

    public long? EmployeeSk { get; set; }

    public string? EffectiveStartDate { get; set; }

    public string? EffectiveEndDate { get; set; }

    public bool? IsCurrent { get; set; }
}
