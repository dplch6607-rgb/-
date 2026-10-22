# Схема классов и компонентов

Диаграммы в формате Mermaid (отображаются на GitHub и в VS Code с расширением Markdown Preview Mermaid).

## Классы

```mermaid
classDiagram
    direction LR

    class Item {
        <<abstract>>
        +sku : str  (read-only)
        +name : str  (read-only)
        +category : str  (read-only)
        +on_hand : int
        +can_issue(quantity) bool
        +can_ever_issue(quantity) bool
        +take(quantity)
        +give_back(quantity)
        +add_stock(amount)
        +needs_attention() str|None
        +describe() str
        +to_dict() dict
    }
    class ReusableTool {
        +total : int
        +available : int
        returnable = True
    }
    class Consumable {
        +quantity : int
        +min_stock : int
        +unit : str
        returnable = False
    }
    class Inventory {
        -_items : list~Item~
        -_by_sku : dict~str, Item~
        -_categories : set~str~
        +add(item)
        +get(sku) Item
        +remove(sku)
        +update(sku, name, category)
        +sorted_by(field, reverse) list
        +search(mode, query) list
    }
    class Loan {
        <<dataclass>>
        loan_id : int
        sku : str
        borrower : str
        quantity : int
        issued_on : date
        returnable : bool
        returned_on : date|None
    }
    class LoanRequest {
        <<dataclass, frozen>>
        borrower : str
        sku : str
        quantity : int
        created_on : date
    }
    class Workshop {
        -_loans : list~Loan~
        -_waitlist : deque~LoanRequest~
        +issue(sku, borrower, quantity) Loan
        +request_item(...) Loan|LoanRequest
        +return_loan(loan_id)
        +restock(sku, amount)
        +build_report() dict
    }

    Item <|-- ReusableTool : является
    Item <|-- Consumable : является
    Workshop *-- Inventory : композиция
    Workshop *-- "0..*" Loan : журнал выдач
    Workshop *-- "0..*" LoanRequest : очередь (deque)
    Inventory *-- "0..*" Item : композиция
    Loan ..> Item : ссылается по sku
```

**Композиция.** `Workshop` создаёт и владеет `Inventory`, списком `Loan` и очередью `LoanRequest`;
`Inventory` владеет объектами `Item`. Эти объекты не живут отдельно от склада.

**Наследование** есть только там, где верно «является»: инструмент *является* предметом склада,
расходник *является* предметом склада. `Loan` и `LoanRequest` — просто данные, поэтому это `dataclass`
без наследования.

## Модули

```mermaid
flowchart TD
    main["main.py<br/>запуск, аргументы, logging"] --> ui["workshop/ui.py<br/>консольное меню, отчёт на экране"]
    main --> storage
    ui --> models["workshop/models.py<br/>Item, Inventory, Workshop, Loan"]
    ui --> storage["workshop/storage.py<br/>CSV-импорт (генератор), JSON"]
    storage --> models
    models --> algorithms["workshop/algorithms.py<br/>поиск и сортировка"]
    models --> exceptions["workshop/exceptions.py<br/>WorkshopError и потомки"]
    storage --> exceptions
    ui --> exceptions
```

## Поток данных при импорте

```mermaid
flowchart LR
    csv[("items.csv")] -->|"read_csv_rows<br/>(генератор)"| v["проверка строки"]
    v -->|"_transform_rows<br/>(генератор)"| t["преобразование типов"]
    t -->|"item_from_dict"| o["создание Item<br/>(property-проверки)"]
    o -->|"Workshop.add_item"| w["обработка:<br/>склад"]
    w -->|"save_state"| json[("state.json")]
    v -. "ошибка строки" .-> log["logging + список отклонённых"]
    o -. "ошибка" .-> log
    w -. "дубликат" .-> log
```
