using System;
using System.Collections.Generic;

namespace LotusApi.Models;

public partial class SchemaChange
{
    public DateTime DetectedAt { get; set; }

    public string TableName { get; set; } = null!;

    public string? ColumnName { get; set; }

    public string ChangeType { get; set; } = null!;
}
