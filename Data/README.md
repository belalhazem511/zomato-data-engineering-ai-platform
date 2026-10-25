# Data preparation guide

The original local CSV files are intentionally excluded from this public repository.

They include operational and potentially personal or sensitive fields such as user names,
email addresses, passwords, restaurant addresses, external links, and license-related
values. Their redistribution rights and privacy status have not been established.

Authorized users should provide their own data through the existing Snowflake RAW/S3
ingestion process. The expected source entities and headers are documented below.

| Entity | Required source fields |
| --- | --- |
| users | `user_id`, `name`, `email`, `Age`, `Gender`, `Marital Status`, `Occupation`, `Monthly Income`, `Educational Qualifications`, `Family size` |
| restaurants | `id`, `name`, `city`, `rating`, `rating_count`, `cost`, `cuisine`, `lic_no` |
| food | `f_id`, `item`, `veg_or_non_veg` |
| menu | `menu_id`, `r_id`, `f_id`, `cuisine`, `price` |
| orders | `order_id`, `order_timestamp`, `order_date`, `user_id`, `r_id`, `restaurant_city`, `cuisine`, `items_count`, `sales_qty`, `subtotal`, `discount`, `delivery_fee`, `gst`, `sales_amount`, `currency`, `payment_method`, `order_status`, `customer_rating`, `delivery_time_min` |
| order_items | `order_item_id`, `order_id`, `r_id`, `f_id`, `price`, `quantity`, `line_amount` |
| reviews | `review_id`, `order_id`, `user_id`, `restaurant_id`, `rating`, `comment`, `review_date` |

Do not upload production, private, or unlicensed data to this repository.
