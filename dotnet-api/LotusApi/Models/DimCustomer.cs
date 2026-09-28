using System;
using System.Collections.Generic;

namespace LotusApi.Models;

public partial class DimCustomer
{
    public string? CustomerId { get; set; }

    public string? FullName { get; set; }

    public string? Gender { get; set; }

    public DateOnly? BirthDate { get; set; }

    public string? Phone { get; set; }

    public string? Email { get; set; }

    public string? City { get; set; }

    public string? Region { get; set; }

    public string? LoyaltyTier { get; set; }

    public DateOnly? RegistrationDate { get; set; }

    public string? BatchId { get; set; }

    public string? AttributeHash { get; set; }

    public long? CustomerSk { get; set; }

    public string? EffectiveStartDate { get; set; }

    public string? EffectiveEndDate { get; set; }

    public bool? IsCurrent { get; set; }
}
