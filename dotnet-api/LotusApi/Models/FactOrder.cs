using System;
using System.Collections.Generic;

namespace LotusApi.Models;

public partial class FactOrder
{
    public string? OrderId { get; set; }

    public DateOnly? OrderDate { get; set; }

    public long? DateId { get; set; }

    public string? CustomerId { get; set; }

    public long? StoreId { get; set; }

    public string? EmployeeId { get; set; }

    public string? PaymentMethod { get; set; }

    public string? OrderStatus { get; set; }

    public double? TotalRevenue { get; set; }

    public double? TotalCost { get; set; }

    public string? FullName { get; set; }

    public string? Gender { get; set; }

    public DateOnly? BirthDate { get; set; }

    public string? Phone { get; set; }

    public string? Email { get; set; }

    public string? City { get; set; }

    public string? Region { get; set; }

    public string? LoyaltyTier { get; set; }

    public DateOnly? RegistrationDate { get; set; }

    public string? AttributeHash { get; set; }

    public long? CustomerSk { get; set; }

    public DateTime? EffectiveStartDate { get; set; }

    public DateTime? EffectiveEndDate { get; set; }

    public bool? IsCurrent { get; set; }

    public double? EmployeeSk { get; set; }

    public DateTime? EffectiveStartDateEmp { get; set; }

    public DateTime? EffectiveEndDateEmp { get; set; }

    public string? BatchId { get; set; }
}
