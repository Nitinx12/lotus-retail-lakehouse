using System;
using System.Collections.Generic;

namespace LotusApi.Models;

public partial class DimCustomersMasked
{
    public string? CustomerId { get; set; }

    public string? NameInitials { get; set; }

    public string? EmailHash { get; set; }

    public string? City { get; set; }

    public string? Region { get; set; }

    public string? LoyaltyTier { get; set; }
}
