using System;
using System.Collections.Generic;

namespace LotusApi.Models;

public partial class FactReturn
{
    public string? ReturnId { get; set; }

    public string? OrderId { get; set; }

    public DateOnly? ReturnDate { get; set; }

    public string? ReturnReason { get; set; }

    public double? ReturnAmount { get; set; }

    public string? RefundMethod { get; set; }

    public string? ReturnStatus { get; set; }

    public long? NItems { get; set; }

    public double? OrderRevenue { get; set; }

    public bool? ReturnOrphan { get; set; }

    public long? CustomerSk { get; set; }

    public double? EmployeeSk { get; set; }

    public long? StoreId { get; set; }

    public string? BatchId { get; set; }
}
